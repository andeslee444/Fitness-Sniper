"""WHO-GETS-IT fallbacks on shared BLI codes (ROADMAP #82).

fct_program_concentration aggregates by BARE pe_bli. On '3010' more than one
member — LPD Flight II (1611N) and Shipboard Tactical Communications (1810N) —
carries published links, so the exporter withholds the bare-key figure from
both member pages (_concentration_for -> None; #70/#82). The rule is on LINKS,
not money: the printed high-confidence figure may be one member's money (on
3010 it is SCN's), and only the unprinted all-links figure pools both
members'. Before this task the two fallback builders still
read the RAW hhi_by_pe: _build_lobbied_by saw a bare-key figure and skipped
the code (the fallback a withheld page needs most), while _build_named_primes
looked up hhi_by_pe[dossier stem] — a SLUG since Sprint E ('3010-SCN') — and
so never saw any concentration at all, and its slug-keyed output was then
looked up by bare pe_bli in _summary_block, so a split member's primes could
never reach its page.

Both builders now take the page's own `concentration_for(pe_bli, account,
organization)`, a slug index, and the page's own `awards_for(pe_bli, account,
organization)`, and key their output by slug (identity for every non-split
program). The awards guard is ROADMAP #80 fix round 1's — each tier's closing
sentence ("not yet crosswalked to award data"; "No contract award is linked
to this line") may not render above THIS member's Related Awards table — made
per member, because the block is now per member. No Postgres, no full export:
the builders are called directly.
"""
from __future__ import annotations

import json

import duckdb

from govbudget.export_site import _build_lobbied_by, _build_named_primes

SCN, OPN = "1611N", "1810N"
FID = "0123456789abcdef"
# Carries BOTH fid spellings on purpose: ROADMAP #80 (Task 7) renamed the
# block's keys to *_all / *_high and replaced the builders' predicate with
# _who_gets_it_fid, which reads program_dollars_high_fact_id. This block
# satisfies either predicate, so the fixture does not depend on task order.
LINKED = {
    "hhi": 8411.8,
    "hhi_all": 8411.8,
    "hhi_high": 8411.8,
    "top_family": "HUNTINGTON INGALLS INDUSTRIES",
    "top_family_all": "HUNTINGTON INGALLS INDUSTRIES",
    "top_family_high": "HUNTINGTON INGALLS INDUSTRIES",
    "family_count": 2,
    "program_dollars": 3.0e9,
    "program_dollars_all": 3.0e9,
    "program_dollars_high": 3.0e9,
    "hhi_fact_id": "f" * 16,
    "hhi_all_fact_id": "f" * 16,
    "hhi_high_fact_id": "f" * 16,
    "program_dollars_fact_id": "d" * 16,
    "program_dollars_all_fact_id": "d" * 16,
    "program_dollars_high_fact_id": "d" * 16,
}
SLUG_INDEX = {
    "3010-SCN": ("3010", SCN, "N"),
    "3010-OPN": ("3010", OPN, "N"),
    "0601101E": ("0601101E", None, "DARPA"),
}
ENTITY_ROWS = [
    ("HUNTINGTON INGALLS INDUSTRIES", "Huntington Ingalls Industries"),
    ("LOCKHEED MARTIN", "Lockheed Martin"),
]


def _withheld_for_3010(pe_bli, account=None, organization=None):
    """The live 3010 shape: both members carry links -> the bare-key figure
    is withheld from both member pages (a rule on links; the printed
    high-confidence figure may be one member's money)."""
    return None if pe_bli == "3010" else LINKED


def _no_awards(pe_bli, account=None, organization=None):
    return []


def _dossier(tmp_path, slug, text):
    d = tmp_path / "dossiers"
    d.mkdir(exist_ok=True)
    (d / f"{slug}.json").write_text(json.dumps({
        "pe_bli": slug.split("-")[0],
        "slug": slug,
        "dossier": {"players": {"claims": [{"text": text, "citation": {"fact_id": FID}}]}},
    }))
    return tmp_path


HII_CLAIM = "Huntington Ingalls Industries builds the LPD Flight II hulls at Ingalls."


# ---------------------------------------------------------------------------
# _build_named_primes
# ---------------------------------------------------------------------------


def test_named_primes_are_keyed_by_slug_and_read_the_members_concentration(tmp_path):
    json_dir = _dossier(tmp_path, "3010-SCN", HII_CLAIM)
    out = _build_named_primes(
        json_dir=json_dir, entity_rows=ENTITY_ROWS,
        concentration_for=_withheld_for_3010, slug_index=SLUG_INDEX,
        cited_fact_ids={FID}, awards_for=_no_awards,
    )
    assert list(out) == ["3010-SCN"]
    assert out["3010-SCN"] == [{
        "name": "Huntington Ingalls Industries",
        "family_key": "HUNTINGTON INGALLS INDUSTRIES",
        "fact_id": FID,
        "public_id": FID[:8],
    }]


def test_named_primes_defer_to_a_members_own_published_concentration(tmp_path):
    json_dir = _dossier(tmp_path, "3010-SCN", HII_CLAIM)
    out = _build_named_primes(
        json_dir=json_dir, entity_rows=ENTITY_ROWS,
        concentration_for=lambda *_: LINKED, slug_index=SLUG_INDEX,
        cited_fact_ids={FID}, awards_for=_no_awards,
    )
    assert out == {}


def test_named_primes_ask_for_the_member_not_the_bare_key(tmp_path):
    seen = []

    def spy(pe_bli, account=None, organization=None):
        seen.append((pe_bli, account, organization))
        return None

    json_dir = _dossier(tmp_path, "3010-SCN", HII_CLAIM)
    _build_named_primes(
        json_dir=json_dir, entity_rows=ENTITY_ROWS, concentration_for=spy,
        slug_index=SLUG_INDEX, cited_fact_ids={FID}, awards_for=_no_awards,
    )
    assert seen == [("3010", SCN, "N")]


def test_named_primes_awards_guard_is_per_member(tmp_path):
    """ROADMAP #80 fix round 1's guard, per member (#82). This tier closes
    "— not yet crosswalked to award data", which is false above a member's
    OWN Related Awards table; a SIBLING's table is not this page's."""
    json_dir = _dossier(tmp_path, "3010-SCN", HII_CLAIM)
    _dossier(json_dir, "3010-OPN", HII_CLAIM)

    def awards(pe_bli, account=None, organization=None):
        return [{"award_piid": "N0002420C0001"}] if (pe_bli, account) == ("3010", SCN) else []

    out = _build_named_primes(
        json_dir=json_dir, entity_rows=ENTITY_ROWS,
        concentration_for=lambda *_: None, slug_index=SLUG_INDEX,
        cited_fact_ids={FID}, awards_for=awards,
    )
    assert list(out) == ["3010-OPN"]


def test_named_primes_for_an_ordinary_program_are_unchanged(tmp_path):
    """A non-split slug is its own pe_bli; a stem outside the index falls back
    to (stem, None, None) — the pre-#82 lookup, byte for byte."""
    json_dir = _dossier(tmp_path, "ATA000", "Lockheed Martin is the prime contractor.")
    seen = []

    def spy(pe_bli, account=None, organization=None):
        seen.append((pe_bli, account, organization))
        return None

    out = _build_named_primes(
        json_dir=json_dir, entity_rows=ENTITY_ROWS, concentration_for=spy,
        slug_index=SLUG_INDEX, cited_fact_ids={FID}, awards_for=_no_awards,
    )
    assert seen == [("ATA000", None, None)]
    assert list(out) == ["ATA000"]


# ---------------------------------------------------------------------------
# _build_lobbied_by
# ---------------------------------------------------------------------------


def _lobby_con():
    con = duckdb.connect()
    con.execute(
        "create table fct_program_lobbying (filing_uuid varchar, pe_bli varchar,"
        " program_title varchar, matched_term varchar, description_snippet varchar,"
        " filing_url varchar, client_name varchar, family_key varchar,"
        " filing_year varchar, evidence_kind varchar)"
    )
    con.execute(
        "insert into fct_program_lobbying values"
        " ('u1','3010','LPD Flight II','3010','...','https://x/','HII',"
        "  'HUNTINGTON INGALLS INDUSTRIES','2025','pe_literal'),"
        " ('u2','0601101E','Defense Research Sciences','DARPA','...','https://y/',"
        "  'LM','LOCKHEED MARTIN','2025','alias')"
    )
    return con


def test_lobbied_by_reaches_a_withheld_member():
    """The defect: a bare-key figure that no page publishes used to suppress
    the lobbying tier on BOTH members."""
    out = _build_lobbied_by(
        con=_lobby_con(), concentration_for=_withheld_for_3010,
        slug_index=SLUG_INDEX, named_primes_by_slug={}, awards_for=_no_awards,
        entity_rows=ENTITY_ROWS,
    )
    assert set(out) == {"3010-SCN", "3010-OPN"}   # DARPA has a published figure
    assert out["3010-SCN"]["families"][0]["family_key"] == "HUNTINGTON INGALLS INDUSTRIES"
    assert out["3010-SCN"]["families"][0]["slug"] == "huntington-ingalls-industries"
    assert out["3010-OPN"] == out["3010-SCN"]


def test_lobbied_by_is_suppressed_by_the_members_own_figure_not_the_bare_keys():
    """'3050' shape: every link sits on the OPN member, which gets the figure;
    the SCN member's absence is genuine and may fall back to lobbying."""
    def conc(pe_bli, account=None, organization=None):
        return LINKED if (pe_bli, account) == ("3010", OPN) else None

    out = _build_lobbied_by(
        con=_lobby_con(), concentration_for=conc, slug_index=SLUG_INDEX,
        named_primes_by_slug={}, awards_for=_no_awards, entity_rows=ENTITY_ROWS,
    )
    assert set(out) == {"3010-SCN", "0601101E"}


def test_lobbied_by_awards_guard_is_per_member():
    """The card's sentence begins "No contract award is linked to this line" —
    it may not render above a member's OWN Related Awards table, but a
    sibling's table is not this page's."""
    def awards(pe_bli, account=None, organization=None):
        return [{"award_piid": "N0002420C0001"}] if (pe_bli, account) == ("3010", SCN) else []

    out = _build_lobbied_by(
        con=_lobby_con(), concentration_for=lambda *_: None, slug_index=SLUG_INDEX,
        named_primes_by_slug={}, awards_for=awards, entity_rows=ENTITY_ROWS,
    )
    assert set(out) == {"3010-OPN", "0601101E"}


def test_lobbied_by_defers_to_a_slug_keyed_named_prime():
    out = _build_lobbied_by(
        con=_lobby_con(), concentration_for=lambda *_: None, slug_index=SLUG_INDEX,
        named_primes_by_slug={"3010-SCN": [{"name": "Huntington Ingalls Industries"}]},
        awards_for=_no_awards, entity_rows=ENTITY_ROWS,
    )
    assert set(out) == {"3010-OPN", "0601101E"}


def test_lobbied_by_keeps_a_page_outside_dim_programs_as_its_own_member():
    """Rollup/decade pages have no dim_programs row and so no slug_index
    entry; they behave exactly as before (identity key, bare lookups)."""
    seen = []

    def spy(pe_bli, account=None, organization=None):
        seen.append((pe_bli, account, organization))
        return None

    out = _build_lobbied_by(
        con=_lobby_con(), concentration_for=spy, slug_index={},
        named_primes_by_slug={}, awards_for=_no_awards, entity_rows=ENTITY_ROWS,
    )
    assert set(out) == {"3010", "0601101E"}
    assert ("3010", None, None) in seen and ("0601101E", None, None) in seen


def test_lobbied_by_never_names_a_multi_token_family():
    con = duckdb.connect()
    con.execute(
        "create table fct_program_lobbying (filing_uuid varchar, pe_bli varchar,"
        " program_title varchar, matched_term varchar, description_snippet varchar,"
        " filing_url varchar, client_name varchar, family_key varchar,"
        " filing_year varchar, evidence_kind varchar)"
    )
    con.execute(
        "insert into fct_program_lobbying values ('u3','3010','LPD Flight II',"
        " 'LPD Flight','...','https://z/','X','BAE SYSTEMS','2025','multi_token')"
    )
    out = _build_lobbied_by(
        con=con, concentration_for=lambda *_: None, slug_index=SLUG_INDEX,
        named_primes_by_slug={}, awards_for=_no_awards, entity_rows=ENTITY_ROWS,
    )
    assert out == {}
