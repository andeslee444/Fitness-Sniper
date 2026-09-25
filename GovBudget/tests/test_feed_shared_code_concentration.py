"""Task 28a — the feed's concentration_shift cards follow the #70/#82 rule.

fct_feed_events computes a concentration_shift card's HHI per (BARE pe_bli,
fiscal_year). On a budget-line code two programs share, that index describes
the contractors of BOTH programs whenever both carry crosswalk links — the #56
fusion. Program pages have withheld the pooled figure in exactly that case
since ROADMAP #70/#82 (`_concentration_for`); the feed never applied the rule.
The feed.json exported on 2026-09-24 carries 34 cards on four shared codes
(0145, 2292, 3010, 3215), each titled with the both-members label and
addressed to the bare /program/{code}/ disambiguation stub, which has no
program_details sidecar — so /feed/ rendered them with no program link, and
gate 8 leg l failed on the two that reach its first 75 cards in chain C run 2.

The rule is ONE predicate, `_concentration_owner`, now called by the program
pages and the feed alike:

  * both members carry links  → the card is WITHHELD, and so are the derived
    citations minted for it (no orphan receipt for a card that is not there);
  * exactly one member does    → the card is that member's: addressed to
    /program/{member slug}/, headed by the member's own title;
  * an ordinary code           → the card is unchanged, byte for byte.

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
    _fetch_program_identity,
    _link_keys,
    _member_pages,
    fact_id_derived,
)

SCN, OPN = "1611N", "1810N"
PMC, WPN = "1109N", "1507N"

# 3010: BOTH members carry a link (the 0145 / 3010 / 3215 shape, 2026-09-24).
# 2292: only the WPN member does (the 2292 shape). Its two members carry
#       DIFFERENT titles here — on the live corpus they share one — so the
#       test can tell "the member's own title" from "the shared-code label".
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

_FEED = [
    # (pe_bli, hhi, matched_dollars, fiscal_year)
    ("3010", 10000.0, 1372594624.0, 2019),
    ("3010", 10000.0, 1297963915.0, 2023),
    ("2292", 10000.0, 232767060.34, 2023),
    ("0601101E", 3200.0, 41000000.0, 2024),
]


def _make_db(tmp_path: Path) -> Path:
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
    for pe, org, piid, name, conf, acct in _LINKS:
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


# The shared-code label every bare-keyed consumer uses (prog_titles) — what the
# pre-28a card led with.
_PROG_TITLES = {
    "3010": "LPD Flight II / Shipboard Tactical Communications",
    "2292": "Naval Strike Missile (Marine Corps) / Naval Strike Missile (NSM)",
    "0601101E": "Defense Research Sciences",
}


def _emit(tmp_path: Path, *, with_identity: bool = True, cited=None,
          section_cap: int = 75, program_page_keys=None):
    root = tmp_path / ("with-identity" if with_identity else "legacy")
    root.mkdir()
    db = _make_db(root)
    con = duckdb.connect(str(db), read_only=True)
    json_dir = root / "json"
    json_dir.mkdir()
    kw = {}
    if with_identity:
        ident, awards_by_pe, member_pages = _identity_inputs(con)
        kw = dict(ident=ident, awards_by_pe=awards_by_pe, member_pages=member_pages)
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


# ---------------------------------------------------------------------------
# the ONE predicate
# ---------------------------------------------------------------------------


class TestConcentrationOwner:
    def _ident(self):
        return _ProgramIdentity([
            (pe, acct, acct_title, org, True)
            for pe, org, _fam, _title, acct, acct_title in _DIM_PROGRAMS
        ])

    def test_an_ordinary_code_owns_its_own_figure(self):
        ident = self._ident()
        assert _concentration_owner(ident, {}, "0601101E") == ("0601101E", None, None)

    def test_two_linked_members_own_nothing(self):
        ident = self._ident()
        links = {("3010", SCN, None): ["a"], ("3010", OPN, None): ["b"]}
        assert _concentration_owner(ident, links, "3010") is None

    def test_the_one_linked_member_owns_the_figure(self):
        ident = self._ident()
        links = {("2292", WPN, None): ["a"], ("2292", PMC, None): []}
        assert _concentration_owner(ident, links, "2292") == ("2292", WPN, None)

    def test_a_shared_code_with_no_link_owns_nothing(self):
        assert _concentration_owner(self._ident(), {}, "2292") is None

    def test_a_single_key_no_member_page_reads_owns_nothing(self):
        # An account-NULL link on an account-split code names BOTH members —
        # the key exists, but no member page is addressed by it.
        ident = self._ident()
        assert _concentration_owner(ident, {("2292", None, None): ["a"]}, "2292") is None


# ---------------------------------------------------------------------------
# the feed follows it
# ---------------------------------------------------------------------------


class TestFeedFollowsTheRule:
    def test_both_members_linked_withholds_every_card_on_the_code(self, tmp_path):
        cards = _cards(_emit(tmp_path))
        assert [c for c in cards if c["pe_bli"] == "3010"] == []

    def test_the_census_line_counts_the_withheld_cards(self, tmp_path, capsys):
        _emit(tmp_path)
        lines = [
            ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("feed: ") and "concentration_shift" in ln
        ]
        assert len(lines) == 1, lines
        assert lines[0].startswith(
            "feed: 2 concentration_shift card(s) withheld on 1 shared code(s)"
            " whose members both carry links (#70/#82 rule)"
        ), lines[0]
        assert "3010" in lines[0]
        assert "1 published under the one member that carries links" in lines[0]
        assert "2292-WPN" in lines[0]

    def test_one_member_linked_addresses_that_members_page(self, tmp_path):
        (card,) = [c for c in _cards(_emit(tmp_path)) if c["pe_bli"] == "2292"]
        assert card["program_url"] == "/program/2292-WPN/"
        assert card["title"] == "Naval Strike Missile (NSM)"
        assert card["headline"].startswith("Naval Strike Missile (NSM) award concentration")
        # the budget-line code, the guid's entity and the company-watch key
        # all stay the bare code the mart keyed the event on
        assert card["pe_bli"] == "2292"

    def test_an_ordinary_card_is_byte_identical(self, tmp_path):
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
