"""ROADMAP #88 — per-event-type feed sidecars: json/feed-sections/{event_type}.json.

/feed/ renders the top _FEED_SECTION_CAP cards per event type statically and
lets the reader "Show all". That button used to fetch the WHOLE feed.json
(881,872 bytes on the 2026-09-04 export) and filter it in the browser —
97% of the bytes discarded when expanding the 24 hidden yoy_swing cards.

The exporter now writes one sidecar per event type carrying ONLY the cards
past the cap, with the two lookups the client twin cannot compute in the
browser (company_slug, has_program_page) pre-resolved from the SAME sources
feed/page.tsx uses for the visible cards. These tests pin that contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import (
    _FEED_SECTION_CAP,
    _emit_feed_sidecar,
)

_SCHEMA = (
    "create table fct_feed_events ("
    " event_type varchar, pe_bli varchar, organization varchar,"
    " family_key varchar, headline_value double, comparison_value double,"
    " pct_change double, fiscal_year integer, units varchar,"
    " detail_json varchar)"
)

# Four concentration_shift cards with DISTINCT matched dollars. The exporter
# ranks a concentration_shift card by its magnitude.to.value, which IS
# comparison_value (matched obligations) — so 40M, 30M, 20M, 10M gives an
# unambiguous descending order.
_CONC_ROWS = (
    "('concentration_shift', '0101213F', NULL, NULL, 3200.0, 40000000.0, NULL, 2024, 'hhi_dollars', NULL),"
    "('concentration_shift', '0201234A', NULL, NULL, 3100.0, 30000000.0, NULL, 2024, 'hhi_dollars', NULL),"
    "('concentration_shift', '0301235N', NULL, NULL, 3000.0, 20000000.0, NULL, 2024, 'hhi_dollars', NULL),"
    "('concentration_shift', '0401236F', NULL, NULL, 2900.0, 10000000.0, NULL, 2024, 'hhi_dollars', NULL)"
)
_ENTRANT_ROW = (
    "('new_entrant', NULL, NULL, 'ACME ROBOTICS', 3100000.0, 2025.0, NULL, 2025, 'dollars', NULL)"
)
_SWING_ROW = (
    "('yoy_swing', '0101213F', 'F', NULL, 106029.5, 59317.5, 78.75, 2026, 'thousands_usd', NULL)"
)
_ALL_ROWS = ", ".join([_CONC_ROWS, _ENTRANT_ROW, _SWING_ROW])


def _emit(tmp_path: Path, rows_sql: str, **kw) -> tuple[Path, int]:
    """Run the feed writer on a fixture mart; return (json_dir, files written).

    Same fixture shape as tests/test_feed_magnitudes.py::_cards.
    """
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    con.execute(_SCHEMA)
    con.execute(f"insert into fct_feed_events values {rows_sql}")
    con.execute("create table dim_pe_titles (pe_bli varchar, title varchar)")
    con.execute("insert into dim_pe_titles values ('0101213F', 'Minuteman Squadrons')")
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    try:
        n = _emit_feed_sidecar(
            json_dir=json_dir, con=con, prog_titles={}, cited_fact_ids=set(), **kw
        )
    finally:
        con.close()
    return json_dir, n


def _section(json_dir: Path, event_type: str) -> dict:
    return json.loads((json_dir / "feed-sections" / f"{event_type}.json").read_text())


class TestCapIsOwnedByTheExporter:
    def test_default_cap_is_75(self):
        # The /feed/ digest cap. Gate 1's /feed/ ceiling was set for 75; it
        # must not be raised for a bigger cap.
        assert _FEED_SECTION_CAP == 75

    def test_feed_json_publishes_the_cap(self, tmp_path):
        json_dir, _ = _emit(tmp_path, _ALL_ROWS)
        feed = json.loads((json_dir / "feed.json").read_text())
        assert feed["section_cap"] == 75

    def test_feed_json_publishes_an_overridden_cap(self, tmp_path):
        json_dir, _ = _emit(tmp_path, _ALL_ROWS, section_cap=2)
        feed = json.loads((json_dir / "feed.json").read_text())
        assert feed["section_cap"] == 2


class TestOneSidecarPerEventType:
    def test_every_event_type_gets_a_file_and_the_count_is_returned(self, tmp_path):
        json_dir, n = _emit(tmp_path, _ALL_ROWS, section_cap=2)
        names = sorted(p.name for p in (json_dir / "feed-sections").glob("*.json"))
        assert names == [
            "concentration_shift.json",
            "new_entrant.json",
            "yoy_swing.json",
        ]
        assert n == 3

    def test_truncated_section_carries_exactly_the_cards_past_the_cap(self, tmp_path):
        json_dir, _ = _emit(tmp_path, _ALL_ROWS, section_cap=2)
        feed = json.loads((json_dir / "feed.json").read_text())
        feed_conc = [c for c in feed["cards"] if c["event_type"] == "concentration_shift"]
        side = _section(json_dir, "concentration_shift")
        assert side["event_type"] == "concentration_shift"
        assert side["section_cap"] == 2
        assert side["shown"] == 2
        assert side["total"] == 4
        # The SAME sequence the page sliced its first `shown` cards from,
        # continued at `shown` — no gap, no overlap, no re-sort.
        assert [c["pe_bli"] for c in side["cards"]] == [c["pe_bli"] for c in feed_conc[2:]]
        assert [c["pe_bli"] for c in side["cards"]] == ["0301235N", "0401236F"]

    def test_non_truncated_section_gets_an_empty_cards_list(self, tmp_path):
        json_dir, _ = _emit(tmp_path, _ALL_ROWS, section_cap=2)
        side = _section(json_dir, "new_entrant")
        assert side["cards"] == []
        assert side["shown"] == 1 and side["total"] == 1

    def test_every_feed_json_card_key_survives_on_the_sidecar_card(self, tmp_path):
        json_dir, _ = _emit(tmp_path, _ALL_ROWS, section_cap=0)
        feed = json.loads((json_dir / "feed.json").read_text())
        feed_by_pe = {
            c["pe_bli"]: c
            for c in feed["cards"]
            if c["event_type"] == "concentration_shift"
        }
        for card in _section(json_dir, "concentration_shift")["cards"]:
            base = feed_by_pe[card["pe_bli"]]
            for k, v in base.items():
                assert card[k] == v, k
            assert set(card) - set(base) == {"company_slug", "has_program_page"}


class TestPreResolvedLookups:
    def test_has_program_page_follows_program_page_keys(self, tmp_path):
        json_dir, _ = _emit(
            tmp_path, _CONC_ROWS, section_cap=0,
            program_page_keys={"0101213F", "0301235N"},
        )
        by_pe = {
            c["pe_bli"]: c["has_program_page"]
            for c in _section(json_dir, "concentration_shift")["cards"]
        }
        assert by_pe == {
            "0101213F": True, "0201234A": False, "0301235N": True, "0401236F": False,
        }

    def test_has_program_page_is_false_when_no_page_universe_is_given(self, tmp_path):
        # Existing callers (the six pre-#88 tests) pass no universe: nothing
        # links, nothing 404s.
        json_dir, _ = _emit(tmp_path, _CONC_ROWS, section_cap=0)
        assert all(
            c["has_program_page"] is False
            for c in _section(json_dir, "concentration_shift")["cards"]
        )

    def test_company_slug_resolves_from_the_top_200_map_else_null(self, tmp_path):
        json_dir, _ = _emit(
            tmp_path, _ENTRANT_ROW + ", " + _SWING_ROW, section_cap=0,
            company_slug_by_family_key={"ACME ROBOTICS": "acme-robotics"},
        )
        (entrant,) = _section(json_dir, "new_entrant")["cards"]
        assert entrant["family_key"] == "ACME ROBOTICS"
        assert entrant["company_slug"] == "acme-robotics"
        (swing,) = _section(json_dir, "yoy_swing")["cards"]
        assert swing["family_key"] is None and swing["company_slug"] is None

    def test_family_outside_the_map_gets_null_not_a_guess(self, tmp_path):
        json_dir, _ = _emit(
            tmp_path, _ENTRANT_ROW, section_cap=0, company_slug_by_family_key={}
        )
        (entrant,) = _section(json_dir, "new_entrant")["cards"]
        assert entrant["company_slug"] is None


class TestKeyedDirectoryHygiene:
    def test_prune_before_emit_removes_a_retired_event_type(self, tmp_path):
        json_dir = tmp_path / "json"
        (json_dir / "feed-sections").mkdir(parents=True)
        stale = json_dir / "feed-sections" / "zeroed_fy2026.json"
        stale.write_text('{"cards": [{"event_type": "zeroed_fy2026"}], "total": 1}')
        _emit(tmp_path, _SWING_ROW)
        assert not stale.exists(), "a retired event type must lose its sidecar"
        assert sorted(
            p.name for p in (json_dir / "feed-sections").glob("*.json")
        ) == ["yoy_swing.json"]

    def test_refuses_an_event_type_that_is_not_a_safe_file_name(self, tmp_path):
        bad = "('../evil', '0101213F', NULL, NULL, 1.0, 2.0, NULL, 2024, 'hhi_dollars', NULL)"
        with pytest.raises(ValueError, match="feed-sections"):
            _emit(tmp_path, bad)

    def test_a_bad_event_type_writes_no_files_at_all(self, tmp_path):
        # Validation is a PRE-PASS: a poisoned mart must not leave a
        # half-written directory behind for prepare-assets to mirror.
        bad = "('../evil', '0101213F', NULL, NULL, 1.0, 2.0, NULL, 2024, 'hhi_dollars', NULL)"
        with pytest.raises(ValueError):
            _emit(tmp_path, _SWING_ROW + ", " + bad)
        assert list((tmp_path / "json" / "feed-sections").glob("*.json")) == []

    def test_negative_cap_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="section_cap"):
            _emit(tmp_path, _SWING_ROW, section_cap=-1)
