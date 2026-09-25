"""Task 28 fix round 1 (B2) — the feed's page key is ONE rule in two languages.

A feed card addresses the /program/{key}/ page named by its program_url, else
its pe_bli. Since Task 28a the two differ on one card shape: a
concentration_shift card on a budget-line code more than one program shares,
published because one member carries every link, whose program_url names that
member's page (/program/2292-WPN/) while its pe_bli stays the bare code.

The rule exists twice:

  * site/src/lib/feed-model.mjs `feedProgramKey` / `feedCardHasProgramPage` —
    what /feed/, the RSS/Atom item links and the program watch feeds resolve a
    card's page with;
  * src/govbudget/export_site.py `_feed_program_key`, through which
    `_emit_feed_section_sidecars` pre-resolves `has_program_page` for the
    cards past the /feed/ digest cap, which the "Show all" client renders
    from without a page listing of its own.

Until this round each side had its own hand-kept table of cases and nothing
compared them. Both now read ONE table,
site/scripts/gates/__tests__/fixtures/feed-program-key.json; the vitest twin is
site/scripts/gates/__tests__/feed-program-key.test.mjs. On a real build gate 8
leg (p) (site/scripts/gates/feed.mjs) holds every shipped sidecar card's
`has_program_page` to the JS answer over the shipped program_details listing.

`has_program_page` is read off the real emitter's output, not recomputed here,
so a change to how the emitter derives it is what this file catches.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from govbudget.export_site import _emit_feed_section_sidecars, _feed_program_key

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "site" / "scripts" / "gates" / "__tests__" / "fixtures" / "feed-program-key.json"
)
TABLE = json.loads(FIXTURE.read_text(encoding="utf-8"))
CASES = TABLE["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_the_page_key_matches_the_shared_table(case):
    assert _feed_program_key(case["card"]) == case["key"]


def test_the_section_sidecar_resolves_has_program_page_as_the_table_says(tmp_path):
    # section_cap=0 puts every card past the cap, so each one is written with
    # the pre-resolved fields the "Show all" client renders from.
    cards = [
        {**case["card"], "event_type": "concentration_shift"} for case in CASES
    ]
    _emit_feed_section_sidecars(
        json_dir=tmp_path,
        cards=cards,
        section_cap=0,
        program_page_keys=frozenset(TABLE["program_pages"]),
        company_slug_by_family_key={},
    )
    written = json.loads(
        (tmp_path / "feed-sections" / "concentration_shift.json").read_text(
            encoding="utf-8"
        )
    )["cards"]
    assert len(written) == len(CASES)
    got = {c["name"]: w["has_program_page"] for c, w in zip(CASES, written)}
    want = {c["name"]: c["has_program_page"] for c in CASES}
    assert got == want


def test_the_table_covers_every_card_shape():
    """Non-vacuity: a table trimmed to the easy cases would still 'agree'."""
    names = " | ".join(c["name"] for c in CASES)
    member = [c for c in CASES if c["key"] and c["key"] != c["card"].get("pe_bli")]
    assert member and all(c["has_program_page"] for c in member), names
    assert any(c["name"].startswith("bare stub") for c in CASES), names
    assert any(c["name"].startswith("ordinary code") for c in CASES), names
    assert any(c["name"].startswith("company card") for c in CASES), names
    assert sum(c["name"].startswith("malformed url") for c in CASES) >= 3, names
    assert {c["has_program_page"] for c in CASES} == {True, False}
