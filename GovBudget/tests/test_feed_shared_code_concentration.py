"""Task 28a — the feed's concentration_shift cards follow the #70/#82 rule.

fct_feed_events computes a concentration_shift card's HHI per (BARE pe_bli,
fiscal_year) over HIGH-confidence crosswalk links only
(dbt/models/marts/fct_feed_events.sql, `prog_family_year`). On a budget-line
code more than one program shares, the program pages have withheld the pooled
concentration block since ROADMAP #70/#82 whenever more than one member
carries published links of any confidence (`_concentration_for`); until this
task the feed did not apply it. The rule is a test on links, not a finding that
a withheld index mixes two programs' money — and in chain C run 2's export
(built 2026-09-19 at e510d19d) none did. A year's index weighs high-confidence
links with positive obligations only: the three 0145-PANMC links are IDV PIIDs
whose transaction rows all carry obligation 0.0, so every 0145 index was
0145-APN's money; on 3010 and 3215 every high link is one member's, so every
3010 index was 3010-SCN's and every 3215 index 3215-WPN's. They are withheld
with the pooled block by the same test, and whether to adopt a money-aware
test instead is an owner decision recorded 2026-09-24.

Chain C run 2's feed.json (built before this task) carries 33 cards on four
shared codes — 0145 ×9, 3010 ×9, 3215 ×9, 2292 ×6 — each headed by the
shared-code title label (both members' titles; 2292's two members share one)
and addressed to the bare /program/{code}/ disambiguation stub, which has no
program_details sidecar; gate 8 leg l failed in that run on the two that reach
its first 75 cards (0145 FY2019 and FY2020).

The rule is ONE predicate, `_concentration_owner`, called by the program pages
and — through `_concentration_page` — by the feed and its citation builder:

  * more than one member key carries published links → the card is
    WITHHELD, and so are the derived citations minted for it (no orphan
    receipt for a card that is not there);
  * exactly one member does, and no other key → the card is that member's:
    addressed to /program/{member slug}/, headed by the member's own title;
  * that member has no page → the export RAISES (an invariant breach, never a
    silent withhold);
  * an ordinary code → the card is unchanged from before Task 28a, pinned
    against a golden the pre-28a emitter (e510d19d) wrote.

These fixtures need no Postgres; tests/test_collision_slugs.py proves the
same through a whole export_site run.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import (
    _ProgramIdentity,
    _build_derived_citation_rows,
    _concentration_owner,
    _emit_feed_sidecar,
    _feed_program_key,
    _fetch_award_link_rows,
    _fetch_member_page_rows,
    _fetch_program_identity,
    _link_keys,
    _member_pages,
    fact_id_derived,
)

SCN, OPN = "1611N", "1810N"
PMC, WPN = "1109N", "1507N"

# 3010: BOTH members carry a link — the shape of 0145, 3010 and 3215 in chain
#       C run 2's export (2026-09-19). SCN's link is high and OPN's medium, as
#       on run 2's 3010 (SCN high ×1 + medium ×5, OPN medium ×3).
# 2292: only the WPN member does — run 2's 2292 (2292-WPN high ×1, 2292-PMC
#       none). Its two members carry DIFFERENT titles here — in run 2's export
#       they share one, "Naval Strike Missile (NSM)" — so the test can tell
#       "the member's own title" from "the shared-code label".
# 0601101E: an ordinary code.
_DIM_PROGRAMS = [
    ("3010", "N", "procurement", "LPD Flight II", SCN, "Shipbuilding and Conversion, Navy"),
    ("3010", "N", "procurement", "Shipboard Tactical Communications", OPN,
     "Other Procurement, Navy"),
    ("2292", "N", "procurement", "Naval Strike Missile (Marine Corps)", PMC,
     "Procurement, Marine Corps"),
    ("2292", "N", "procurement", "Naval Strike Missile (NSM)", WPN,
     "Weapons Procurement, Navy"),
    ("0601101E", "DARPA", "rdte", "Defense Research Sciences", None, None),
]

_LINKS = [
    # (pe_bli, organization, award_piid, recipient, confidence, account)
    ("3010", "N", "N0002420C0001", "Huntington Ingalls", "high", SCN),
    ("3010", "N", "N0003917D0006", "Serco", "medium", OPN),
    ("2292", "N", "N0002419C5603", "Raytheon", "high", WPN),
    ("0601101E", "DARPA", "W911QX-24-C-0001", "Lockheed Martin", "high", None),
]

# A link on 2292 whose account is NULL: its split key names neither member
# page (an account NULL names every member), so it is filed under a key no
# member page reads — the shape _write_all_sidecars' "awards:" diagnostic
# prints. Zero in chain C run 2's export (its log carries no such line).
_UNREAD_2292_LINK = ("2292", "N", "N0002421C0042", "Unknown Co", "medium", None)

_FEED = [
    # (pe_bli, hhi, matched_dollars, fiscal_year)
    ("3010", 10000.0, 1372594624.0, 2019),
    ("3010", 10000.0, 1297963915.0, 2023),
    ("2292", 10000.0, 232767060.34, 2023),
    ("0601101E", 3200.0, 41000000.0, 2024),
]


def _make_db(tmp_path: Path, *, extra_links=()) -> Path:
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table dim_programs (pe_bli varchar, org varchar,"
        " exhibit_family varchar, title varchar, project_count integer,"
        " fy2024_actual_millions double, fully_reconciled boolean,"
        " account varchar, account_title varchar)"
    )
    for pe, org, fam, title, acct, acct_title in _DIM_PROGRAMS:
        con.execute(
            "insert into dim_programs values (?, ?, ?, ?, 0, 1.0, true, ?, ?)",
            [pe, org, fam, title, acct, acct_title],
        )
    con.execute(
        "create table fct_budget_to_awards (pe_bli varchar, exhibit varchar,"
        " fiscal_year integer, organization varchar, award_piid varchar,"
        " recipient_name varchar, recipient_uei varchar, method varchar,"
        " account varchar, confidence varchar, program_title varchar)"
    )
    for pe, org, piid, name, conf, acct in (*_LINKS, *extra_links):
        con.execute(
            "insert into fct_budget_to_awards values"
            " (?, 'P-1', 2026, ?, ?, ?, 'UEI', 'fpds-ap', ?, ?, NULL)",
            [pe, org, piid, name, acct, conf],
        )
    con.execute(
        "create table fct_feed_events (event_type varchar, pe_bli varchar,"
        " organization varchar, family_key varchar, headline_value double,"
        " comparison_value double, pct_change double, fiscal_year integer,"
        " units varchar, detail_json varchar)"
    )
    for pe, hhi, dollars, fy in _FEED:
        con.execute(
            "insert into fct_feed_events values ('concentration_shift', ?,"
            " NULL, NULL, ?, ?, NULL, ?, 'hhi_dollars', NULL)",
            [pe, hhi, dollars, fy],
        )
    con.execute("create table dim_pe_titles (pe_bli varchar, title varchar)")
    con.close()
    return db


def _identity_inputs(con):
    """(ident, awards_by_pe, member_pages) built the way _write_all_sidecars
    builds them: the one identity map, the published links keyed by split
    key, and each member page's (slug, title)."""
    ident = _fetch_program_identity(con)
    awards_by_pe = _link_keys(ident, _fetch_award_link_rows(con))
    member_pages = _member_pages(ident, [
        (pe, acct, acct_title, org, title)
        for pe, org, _fam, title, acct, acct_title in _DIM_PROGRAMS
    ])
    return ident, awards_by_pe, member_pages


def _ident() -> _ProgramIdentity:
    return _ProgramIdentity([
        (pe, acct, acct_title, org, True)
        for pe, org, _fam, _title, acct, acct_title in _DIM_PROGRAMS
    ])


# The shared-code label every bare-keyed consumer uses (prog_titles) — what the
# pre-28a card led with.
_PROG_TITLES = {
    "3010": "LPD Flight II / Shipboard Tactical Communications",
    "2292": "Naval Strike Missile (Marine Corps) / Naval Strike Missile (NSM)",
    "0601101E": "Defense Research Sciences",
}


def _emit(tmp_path: Path, *, with_identity: bool = True, cited=None,
          section_cap: int = 75, program_page_keys=None, extra_links=(),
          member_pages=None):
    root = tmp_path / ("with-identity" if with_identity else "legacy")
    root.mkdir()
    db = _make_db(root, extra_links=extra_links)
    con = duckdb.connect(str(db), read_only=True)
    json_dir = root / "json"
    json_dir.mkdir()
    kw = {}
    if with_identity:
        ident, awards_by_pe, pages = _identity_inputs(con)
        kw = dict(
            ident=ident, awards_by_pe=awards_by_pe,
            member_pages=pages if member_pages is None else member_pages,
        )
    try:
        _emit_feed_sidecar(
            json_dir=json_dir, con=con, prog_titles=_PROG_TITLES,
            cited_fact_ids=cited if cited is not None else set(),
            section_cap=section_cap, program_page_keys=program_page_keys, **kw,
        )
    finally:
        con.close()
    return json_dir


def _cards(json_dir: Path) -> list[dict]:
    return json.loads((json_dir / "feed.json").read_text())["cards"]


def _census(out: str) -> str:
    lines = [
        ln for ln in out.splitlines()
        if ln.startswith("feed: ") and "concentration_shift" in ln
    ]
    assert len(lines) == 1, lines
    return lines[0]


# ---------------------------------------------------------------------------
# the ONE predicate
# ---------------------------------------------------------------------------


class TestConcentrationOwner:
    def test_an_ordinary_code_owns_its_own_figure(self):
        assert _concentration_owner(_ident(), {}, "0601101E") == ("0601101E", None, None)

    def test_two_linked_members_own_nothing(self):
        links = {("3010", SCN, None): ["a"], ("3010", OPN, None): ["b"]}
        assert _concentration_owner(_ident(), links, "3010") is None

    def test_the_one_linked_member_owns_the_figure(self):
        links = {("2292", WPN, None): ["a"], ("2292", PMC, None): []}
        assert _concentration_owner(_ident(), links, "2292") == ("2292", WPN, None)

    def test_a_shared_code_with_no_link_owns_nothing(self):
        assert _concentration_owner(_ident(), {}, "2292") is None

    def test_a_single_key_no_member_page_reads_owns_nothing(self):
        # An account-NULL link on an account-split code names BOTH members —
        # the key exists, but no member page is addressed by it.
        assert _concentration_owner(_ident(), {("2292", None, None): ["a"]}, "2292") is None

    def test_a_member_beside_a_key_no_member_page_reads_owns_nothing(self):
        # The figure counts the unread key's links too, so it is not WPN's.
        links = {("2292", WPN, None): ["a"], ("2292", None, None): ["b"]}
        assert _concentration_owner(_ident(), links, "2292") is None


# ---------------------------------------------------------------------------
# only a member key is a member (ROADMAP #82's "more than one member")
# ---------------------------------------------------------------------------


class TestOnlyMemberKeysCountAsMembers:
    """A link filed under a key no member page reads is not a member carrying
    links. Counting it as one made the census say "whose members both carry
    links" and set the page's shared-code sentence ("more than one of them
    carries linked awards") on a code where ONE member does."""

    _ONE_PLUS_UNREAD = {("2292", WPN, None): ["a"], ("2292", None, None): ["b"]}
    _BOTH = {("3010", SCN, None): ["a"], ("3010", OPN, None): ["b"]}

    def test_the_linked_member_keys_leave_out_an_unread_key(self):
        from govbudget.export_site import _linked_member_keys

        assert _linked_member_keys(_ident(), self._ONE_PLUS_UNREAD, "2292") == {
            ("2292", WPN, None)
        }
        assert _linked_member_keys(_ident(), self._BOTH, "3010") == {
            ("3010", SCN, None), ("3010", OPN, None)
        }

    def test_the_shared_code_reason_needs_more_than_one_linked_member(self):
        from govbudget.export_site import _withheld_as_shared

        ident = _ident()
        assert _withheld_as_shared(ident, self._BOTH, "3010", SCN) is True
        assert _withheld_as_shared(ident, self._BOTH, "3010", OPN) is True
        # one member plus an unread key: withheld, but NOT for the reason the
        # page's shared-code sentence gives
        assert _withheld_as_shared(ident, self._ONE_PLUS_UNREAD, "2292", WPN) is False
        assert _withheld_as_shared(ident, self._ONE_PLUS_UNREAD, "2292", PMC) is False
        # an unlinked member of a two-linked code does not exist here; an
        # ordinary code never takes the shared-code sentence
        assert _withheld_as_shared(
            ident, {("0601101E", None, None): ["x"]}, "0601101E"
        ) is False

    def test_the_census_does_not_count_an_unread_key_as_a_member(
        self, tmp_path, capsys
    ):
        cards = _cards(_emit(tmp_path, extra_links=[_UNREAD_2292_LINK]))
        assert [c for c in cards if c["pe_bli"] == "2292"] == []
        line = _census(capsys.readouterr().out)
        assert line.startswith(
            "feed: 2 concentration_shift card(s) withheld on 1 shared code(s)"
            " on which more than one member key carries published links"
            " (#70/#82 rule): 3010;"
        ), line
        assert (
            "; 1 withheld on 1 shared code(s) on which no single member page"
            " carries the links: 2292" in line
        ), line
        # the unread key is named on its own, never counted as a member
        assert "('2292', None, None)" in line, line


# ---------------------------------------------------------------------------
# the feed follows it
# ---------------------------------------------------------------------------


class TestFeedFollowsTheRule:
    def test_both_members_linked_withholds_every_card_on_the_code(self, tmp_path):
        cards = _cards(_emit(tmp_path))
        assert [c for c in cards if c["pe_bli"] == "3010"] == []

    def test_the_census_line_counts_the_withheld_cards(self, tmp_path, capsys):
        _emit(tmp_path)
        line = _census(capsys.readouterr().out)
        assert line == (
            "feed: 2 concentration_shift card(s) withheld on 1 shared code(s)"
            " on which more than one member key carries published links"
            " (#70/#82 rule): 3010; 1 published under the one member that"
            " carries links: 2292-WPN"
        ), line

    def test_one_member_linked_addresses_that_members_page(self, tmp_path):
        (card,) = [c for c in _cards(_emit(tmp_path)) if c["pe_bli"] == "2292"]
        assert card["program_url"] == "/program/2292-WPN/"
        assert card["title"] == "Naval Strike Missile (NSM)"
        assert card["headline"].startswith("Naval Strike Missile (NSM) award concentration")
        # the budget-line code, the guid's entity and the company-watch key
        # all stay the bare code the mart keyed the event on
        assert card["pe_bli"] == "2292"

    def test_an_ordinary_card_does_not_depend_on_the_identity(self, tmp_path):
        """Identity-independence only: with and without the identity inputs
        today's emitter writes the same ordinary card. That it is also the
        card the pre-28a emitter wrote is the golden test below."""
        new = [c for c in _cards(_emit(tmp_path)) if c["pe_bli"] == "0601101E"]
        legacy = [
            c for c in _cards(_emit(tmp_path, with_identity=False))
            if c["pe_bli"] == "0601101E"
        ]
        assert len(new) == 1
        assert json.dumps(new, sort_keys=True) == json.dumps(legacy, sort_keys=True)
        assert new[0]["program_url"] == "/program/0601101E/"
        assert new[0]["title"] == "Defense Research Sciences"

    def test_feed_total_counts_only_published_cards(self, tmp_path):
        payload = json.loads((_emit(tmp_path) / "feed.json").read_text())
        assert payload["total"] == len(payload["cards"]) == 2

    def test_the_section_sidecar_resolves_the_members_page(self, tmp_path):
        # section_cap=0 puts every card in the sidecar ("Show all").
        json_dir = _emit(
            tmp_path, section_cap=0,
            program_page_keys=frozenset({"2292-PMC", "2292-WPN", "3010-SCN",
                                         "3010-OPN", "0601101E"}),
        )
        sec = json.loads(
            (json_dir / "feed-sections" / "concentration_shift.json").read_text()
        )
        assert sec["total"] == 2
        by_pe = {c["pe_bli"]: c for c in sec["cards"]}
        assert set(by_pe) == {"2292", "0601101E"}
        assert by_pe["2292"]["has_program_page"] is True
        assert by_pe["0601101E"]["has_program_page"] is True


# ---------------------------------------------------------------------------
# an owner without a member page is an invariant breach, not a withhold
# ---------------------------------------------------------------------------


class TestAnOwnerWithoutAPageIsLoud:
    """On a real lake the identity map and the member-page rows both come
    from dim_programs, so a member that owns a figure always has a page. A
    silent withhold would hide the day they disagree — and the feed used to
    withhold such a card while the citation builder, which never asked,
    minted its receipts (orphans). Both now go through one decision, and it
    raises."""

    def test_the_decision_raises_naming_the_code_and_the_owner(self):
        from govbudget.export_site import _concentration_page

        with pytest.raises(ValueError, match=r"'2292'.*'1507N'"):
            _concentration_page(_ident(), {("2292", WPN, None): ["a"]}, {}, "2292")

    def test_the_decision_answers_every_other_case(self):
        from govbudget.export_site import _concentration_page

        ident = _ident()
        pages = _member_pages(ident, [
            (pe, acct, acct_title, org, title)
            for pe, org, _fam, title, acct, acct_title in _DIM_PROGRAMS
        ])
        assert _concentration_page(
            ident, {("2292", WPN, None): ["a"]}, pages, "2292"
        ) == ("2292-WPN", "Naval Strike Missile (NSM)")
        assert _concentration_page(
            ident, {("3010", SCN, None): ["a"], ("3010", OPN, None): ["b"]},
            pages, "3010",
        ) is None
        # an ordinary code is its own page; the caller keeps its own title
        assert _concentration_page(ident, {}, pages, "0601101E") == ("0601101E", None)

    def test_the_feed_raises_rather_than_withholding(self, tmp_path):
        with pytest.raises(ValueError, match=r"'2292'.*'1507N'"):
            _emit(tmp_path, member_pages={})

    def test_the_citation_builder_raises_on_the_same_breach(
        self, tmp_path, monkeypatch
    ):
        # The builder reads its member pages itself (it runs before the page
        # rows exist); hand it rows that lack the owning member.
        import govbudget.export_site as es

        monkeypatch.setattr(es, "_member_pages", lambda ident, rows: {})
        with pytest.raises(ValueError, match=r"'2292'.*'1507N'"):
            _build_derived_citation_rows(
                duckdb_path=_make_db(tmp_path), bl_rows=[], citation_rows=[],
            )


# ---------------------------------------------------------------------------
# citations move with the cards
# ---------------------------------------------------------------------------


def _fid(pe: str, fy: int, metric: str) -> str:
    return fact_id_derived("feed", f"concentration_shift|{pe}|{fy}", metric)


class TestCitationsMoveWithTheCards:
    def test_withheld_cards_mint_no_citation(self, tmp_path):
        rows = _build_derived_citation_rows(
            duckdb_path=_make_db(tmp_path), bl_rows=[], citation_rows=[],
        )
        fids = {r[0] for r in rows}
        for fy in (2019, 2023):
            assert _fid("3010", fy, "hhi") not in fids
            assert _fid("3010", fy, "matched_dollars") not in fids
        assert _fid("2292", 2023, "hhi") in fids
        assert _fid("2292", 2023, "matched_dollars") in fids
        assert _fid("0601101E", 2024, "hhi") in fids

    def test_every_minted_feed_citation_is_cited_by_a_card(self, tmp_path):
        """No orphan in either direction: each concentration_shift citation the
        builder mints is the figure or magnitude receipt of a published card,
        and each published card's receipts resolve."""
        sub = tmp_path / "cit"
        sub.mkdir()
        rows = _build_derived_citation_rows(
            duckdb_path=_make_db(sub), bl_rows=[], citation_rows=[],
        )
        minted = {
            r[0] for r in rows
            if r[0] in {_fid(pe, fy, m) for pe, _h, _d, fy in _FEED
                        for m in ("hhi", "matched_dollars")}
        }
        cards = _cards(_emit(tmp_path, cited=minted))
        referenced = set()
        for c in cards:
            if c["event_type"] != "concentration_shift":
                continue
            assert c["figure_fact_id"] is not None, c
            assert c["magnitude"]["to"]["fact_id"] is not None, c
            referenced |= {c["figure_fact_id"], c["magnitude"]["to"]["fact_id"]}
        assert minted == referenced


# ---------------------------------------------------------------------------
# the citation builder's member-page read fails loudly, and says what failed
# ---------------------------------------------------------------------------


class TestTheMemberPageReadIsNarrow:
    """_fetch_member_page_rows (the citation builder's member pages) used to
    turn ANY failed read into [] — and _concentration_page then raised that
    the identity map and the page rows disagree, blaming a disagreement for
    what was a failed read. Only an ABSENT dim_programs means "no rows"
    (the _require_account_column semantics); any other failure propagates
    with its own message."""

    def test_an_absent_dim_programs_gives_no_rows(self):
        con = duckdb.connect()
        try:
            assert _fetch_member_page_rows(con) == []
        finally:
            con.close()

    def test_a_failed_read_propagates(self):
        con = duckdb.connect()
        try:
            con.execute(
                "create table dim_programs (pe_bli varchar, account varchar,"
                " account_title varchar, org varchar)"
            )
            with pytest.raises(duckdb.BinderException, match="title"):
                _fetch_member_page_rows(con)
        finally:
            con.close()

    def test_the_citation_builder_names_the_failed_read(self, tmp_path):
        # dim_programs without `title`: the identity read (account,
        # account_title, org, exhibit_family) succeeds, the member-page read
        # cannot. The builder must stop on the read, not on a "disagree".
        db = _make_db(tmp_path)
        con = duckdb.connect(str(db))
        con.execute("alter table dim_programs drop column title")
        con.close()
        with pytest.raises(duckdb.BinderException, match="title"):
            _build_derived_citation_rows(
                duckdb_path=db, bl_rows=[], citation_rows=[],
            )


# ---------------------------------------------------------------------------
# ordinary cards are the cards the PRE-28a emitter wrote (golden)
# ---------------------------------------------------------------------------
#
# tests/fixtures/feed/ordinary_cards_pre28a.json was written by the emitter
# as it stood at e510d19d, the commit before Task 28a — never by today's
# code: `git show e510d19d:GovBudget/src/govbudget/export_site.py` saved
# outside the tree as export_site_pre28a.py, imported under that name via
# PYTHONPATH, and run through golden_emit(...) below on _make_golden_db's
# fixture with golden_emit_kwargs(). The file's "produced_by" field repeats
# the recipe. Regenerate it only from a pre-28a emitter.
#
# Every mart event type is present, not just concentration_shift: Task 28a
# moved the card's program_url into a per-card variable set at the loop's top
# and re-keyed the section sidecars' has_program_page — both touch every card.

_GOLDEN = Path(__file__).parent / "fixtures" / "feed" / "ordinary_cards_pre28a.json"

_GOLDEN_EXTRA_FEED = [
    # (event_type, pe_bli, organization, family_key, headline_value,
    #  comparison_value, pct_change, fiscal_year, units)
    ("yoy_swing", "0603XYZ", "DARPA", None, 150000.0, 100000.0, 50.0, 2026,
     "thousands_usd"),
    ("zeroed_fy2026", "0604ABC", "A", None, 5000.0, 0.0, None, 2026,
     "thousands_usd"),
    ("new_entrant", None, None, "ACME", 2500000.0, 2024.0, None, 2024,
     "dollars"),
]

_SHARED_CODES = frozenset({"3010", "2292"})


def _make_golden_db(root: Path) -> Path:
    db = _make_db(root)
    con = duckdb.connect(str(db))
    for row in _GOLDEN_EXTRA_FEED:
        con.execute(
            "insert into fct_feed_events values (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            list(row),
        )
    con.close()
    return db


def golden_emit_kwargs() -> dict:
    """What BOTH emitters are handed: the pre-28a one that wrote the golden
    and today's. Every receipt the ordinary cards can carry resolves, so the
    fact ids and headline segments are pinned too; 0604ABC has no page, so a
    False has_program_page is pinned beside the True ones."""
    cited = {
        _fid("0601101E", 2024, "hhi"),
        _fid("0601101E", 2024, "matched_dollars"),
        *(fact_id_derived("trajectory", "0603XYZ|DARPA", m)
          for m in ("fy2025_total", "fy2026_total", "fy2526_change")),
        *(fact_id_derived("trajectory", "0604ABC|A", m)
          for m in ("fy2025_total", "fy2026_total", "fy2526_change")),
        fact_id_derived("feed", "new_entrant|ACME", "total_obligation"),
    }
    return dict(
        prog_titles={**_PROG_TITLES, "0603XYZ": "Hypersonic Test Bed",
                     "0604ABC": "Legacy Tactical Radio"},
        cited_fact_ids=cited,
        section_cap=0,
        program_page_keys=frozenset({"0601101E", "0603XYZ", "2292-PMC",
                                     "2292-WPN", "3010-SCN", "3010-OPN"}),
        fy26_split_by_pe={"0603XYZ": {"has_reconciliation": True,
                                      "discretionary": 120000.0,
                                      "reconciliation": 30000.0}},
        company_slug_by_family_key={"ACME": "acme"},
    )


def golden_emit(emit_feed_sidecar, root: Path, *, with_identity: bool) -> dict:
    """Run an _emit_feed_sidecar on the golden fixture and return every card
    NOT on a shared code: feed.json's, and each section sidecar's."""
    root.mkdir(parents=True, exist_ok=True)
    db = _make_golden_db(root)
    con = duckdb.connect(str(db), read_only=True)
    json_dir = root / "json"
    json_dir.mkdir()
    kw = golden_emit_kwargs()
    if with_identity:
        ident, awards_by_pe, member_pages = _identity_inputs(con)
        kw.update(ident=ident, awards_by_pe=awards_by_pe, member_pages=member_pages)
    try:
        emit_feed_sidecar(json_dir=json_dir, con=con, **kw)
    finally:
        con.close()

    def ordinary(cards):
        return [c for c in cards if c.get("pe_bli") not in _SHARED_CODES]

    return {
        "feed_cards": ordinary(
            json.loads((json_dir / "feed.json").read_text())["cards"]
        ),
        "section_cards": {
            p.stem: ordinary(json.loads(p.read_text())["cards"])
            for p in sorted((json_dir / "feed-sections").glob("*.json"))
        },
    }


def test_ordinary_cards_are_the_cards_the_pre_28a_emitter_wrote(tmp_path):
    golden = json.loads(_GOLDEN.read_text())
    assert "e510d19d" in golden["produced_by"]
    # an empty golden would pass trivially: one card of each mart type
    assert sorted(c["event_type"] for c in golden["feed_cards"]) == [
        "concentration_shift", "new_entrant", "yoy_swing", "zeroed_fy2026",
    ]
    now = golden_emit(_emit_feed_sidecar, tmp_path / "now", with_identity=True)
    # json.dumps(sort_keys=True) is how _write_json serializes every card
    assert json.dumps(now["feed_cards"], sort_keys=True) == json.dumps(
        golden["feed_cards"], sort_keys=True
    )
    assert json.dumps(now["section_cards"], sort_keys=True) == json.dumps(
        golden["section_cards"], sort_keys=True
    )


# ---------------------------------------------------------------------------
# the page a card addresses (mirror of site/src/lib/feed-model.mjs)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("card, key", [
    ({"pe_bli": "2292", "program_url": "/program/2292-WPN/"}, "2292-WPN"),
    ({"pe_bli": "0601101E", "program_url": "/program/0601101E/"}, "0601101E"),
    ({"pe_bli": "0603XYZ", "program_url": None}, "0603XYZ"),
    ({"pe_bli": None, "program_url": None, "family_key": "ACME"}, None),
])
def test_feed_program_key(card, key):
    assert _feed_program_key(card) == key
