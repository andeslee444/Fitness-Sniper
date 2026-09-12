"""Regression tests for _emit_dossier_sidecars (#52 fallout).

THE DEFECT THIS GUARDS AGAINST: the #52 lobbying evidence-tier fix legitimately
retracted single-common-word LDA matches from fct_program_lobbying, which
orphaned 27 dossier "players" claims across 5 of the 50 committed research
dossiers — each claim's cited fact_id no longer resolved in citations.json.
`govbudget dossiers collect` rejects an ENTIRE dossier file the moment any one
claim's citation fails to resolve, which — applied here — would have dropped
5 dossiers to 45 and failed verify-phase5b3's dossiers_present check (every
top-50 pe_bli must have a file).

THE FIX: _emit_dossier_sidecars applies a claim-level rule instead of a
file-level one — drop the individual claim whose citation no longer
resolves, keep the dossier and every other claim, and record how many were
dropped. These tests pin exactly that: a dossier with one bad claim must
still be WRITTEN, with the bad claim gone and the good ones intact — never
"the whole file disappears" the way collect()'s stricter rule would.
"""
from __future__ import annotations

import json
from pathlib import Path

from govbudget.export_site import _emit_dossier_sidecars

GOOD_FACT = "aaaaaaaaaaaaaaaa"
BAD_FACT = "bbbbbbbbbbbbbbbb"
GOOD_URL = "https://example.gov/good-source"
BAD_URL = "https://example.gov/gone-source"


def _sections(what_it_is, why_it_matters, players, recent=None):
    def _sec(claims):
        return {"claims": claims}

    return {
        "what_it_is": _sec(what_it_is),
        "why_it_matters": _sec(why_it_matters),
        "players": _sec(players),
        "recent_developments": _sec(recent or []),
    }


def _claim(text: str, *, fact_id: str | None = None, url: str | None = None) -> dict:
    citation = {"fact_id": fact_id} if fact_id else {"url": url}
    return {"text": text, "citation": citation}


def _write_raw(raw_dir: Path, pe_bli: str, dossier: dict, *, model: str = "claude-opus-4-8") -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "custom_id": f"dossier-{pe_bli}",
        "batch_id": "batch_test",
        "collected_at": "2026-08-08T00:00:00+00:00",
        "message": {
            "model": model,
            "content": [{"type": "text", "text": json.dumps(dossier)}],
        },
    }
    (raw_dir / f"{pe_bli}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_dossier_with_one_bad_claim_is_kept_not_dropped(tmp_path):
    """THE regression: a claim citing a dead fact_id is removed; the dossier
    itself, and every OTHER claim in it, survive — it must not disappear."""
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(
        raw_dir,
        "0604874C",
        _sections(
            what_it_is=[_claim("It is a thing.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
            players=[
                _claim("Lockheed lobbied on it.", fact_id=GOOD_FACT),
                _claim("Boeing lobbied on it too.", fact_id=BAD_FACT),
            ],
        ),
    )
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
    )

    assert result["written"] == 1
    assert result["total_dropped"] == 1
    assert result["dropped_by_pe"] == {"0604874C": 1}

    out = json.loads((json_dir / "dossiers" / "0604874C.json").read_text())
    assert out["dropped_claims"] == 1
    # The good claim in "players" survives; the bad one is gone — not the
    # whole section, not the whole file.
    players_claims = out["dossier"]["players"]["claims"]
    assert len(players_claims) == 1
    assert players_claims[0]["citation"]["fact_id"] == GOOD_FACT
    # Untouched sections are fully intact.
    assert len(out["dossier"]["what_it_is"]["claims"]) == 1
    assert len(out["dossier"]["why_it_matters"]["claims"]) == 1


def test_a_required_section_emptied_entirely_still_ships_the_file(tmp_path):
    """The exact 0603896C shape: EVERY players claim is unresolvable. The
    dossier is still written (players: []), not rejected outright — a
    file-level reject is collect()'s job for a FRESH batch, not this
    function's job for an already-published dossier gone stale."""
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(
        raw_dir,
        "0603896C",
        _sections(
            what_it_is=[_claim("It is a thing.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
            players=[
                _claim("Lockheed lobbied on it.", fact_id=BAD_FACT),
                _claim("Boeing lobbied on it too.", fact_id=BAD_FACT),
            ],
        ),
    )
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
    )

    assert result["written"] == 1
    assert result["dropped_by_pe"] == {"0603896C": 2}
    out = json.loads((json_dir / "dossiers" / "0603896C.json").read_text())
    assert out["dossier"]["players"]["claims"] == []
    assert out["dropped_claims"] == 2
    # what_it_is / why_it_matters are untouched — only players emptied.
    assert len(out["dossier"]["what_it_is"]["claims"]) == 1
    assert len(out["dossier"]["why_it_matters"]["claims"]) == 1


def test_url_citation_not_in_snapshot_index_is_also_dropped(tmp_path):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(
        raw_dir,
        "TEST01",
        _sections(
            what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
            players=[
                _claim("News says X.", url=GOOD_URL),
                _claim("News says Y.", url=BAD_URL),
            ],
        ),
    )
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls={GOOD_URL},
    )

    assert result["dropped_by_pe"] == {"TEST01": 1}
    out = json.loads((json_dir / "dossiers" / "TEST01.json").read_text())
    players_claims = out["dossier"]["players"]["claims"]
    assert len(players_claims) == 1
    assert players_claims[0]["citation"]["url"] == GOOD_URL


def test_dossier_with_nothing_dropped_reports_zero(tmp_path):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(
        raw_dir,
        "CLEAN01",
        _sections(
            what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
            players=[_claim("Someone lobbied.", fact_id=GOOD_FACT)],
        ),
    )
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
    )

    assert result["total_dropped"] == 0
    assert result["dropped_by_pe"] == {}
    out = json.loads((json_dir / "dossiers" / "CLEAN01.json").read_text())
    assert out["dropped_claims"] == 0


def test_batch_meta_json_is_not_treated_as_a_dossier(tmp_path):
    """data/research/dossiers-raw/batch_meta.json sits alongside the 50
    PE-named archives (submit()'s own bookkeeping file) — it must be
    skipped, not written out as a bogus 'dossier' for pe_bli 'batch_meta'."""
    raw_dir = tmp_path / "dossiers-raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "batch_meta.json").write_text(
        json.dumps({"batch_id": "batch_test", "requests": 1}), encoding="utf-8"
    )
    _write_raw(
        raw_dir,
        "REAL01",
        _sections(
            what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
            players=[_claim("Someone lobbied.", fact_id=GOOD_FACT)],
        ),
    )
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
    )

    assert result["written"] == 1
    assert not (json_dir / "dossiers" / "batch_meta.json").exists()
    assert (json_dir / "dossiers" / "REAL01.json").exists()


def test_unreadable_raw_file_is_skipped_not_fatal(tmp_path):
    raw_dir = tmp_path / "dossiers-raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "BROKEN01.json").write_text("{not valid json", encoding="utf-8")
    _write_raw(
        raw_dir,
        "REAL02",
        _sections(
            what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
            players=[_claim("Someone lobbied.", fact_id=GOOD_FACT)],
        ),
    )
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
    )

    assert result["written"] == 1
    assert any("BROKEN01" in s for s in result["skipped"])
    assert (json_dir / "dossiers" / "REAL02.json").exists()


# ---------------------------------------------------------------------------
# chain-B fix 3 — a raw archive keyed by its PAGE
#
# `dossiers collect` names a raw archive from the request's custom_id, which is
# now the page identity ("3010-SCN") wherever a shared BLI code's two members
# are two pages. Two things then had to change here, and both are measured
# defects rather than hypotheticals:
#
#   (1) the top-50 membership seed (program_categories.csv) is keyed by the
#       bare CODE, so a page-keyed archive looked like a pe_bli outside the
#       top-50 and was RETIRED on sight — its sidecar unlinked;
#   (2) the older bare-keyed archive for the same page is still on disk (paid
#       research is never deleted) and sorted() let it write LAST, silently
#       overwriting the regenerated dossier with the superseded one.
# ---------------------------------------------------------------------------

_SPLIT_PE, _SPLIT_SCN = "3010", "3010-SCN"


def _clean(text: str = "A thing."):
    return _sections(
        what_it_is=[_claim(text, fact_id=GOOD_FACT)],
        why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
        players=[_claim("A prime built it.", fact_id=GOOD_FACT)],
    )


def test_a_page_keyed_archive_is_written_at_its_page_and_kept_in_the_top_set(
    tmp_path,
):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, _SPLIT_SCN, _clean("The member's own dossier."))
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
        # the seed is keyed by the CODE — the page must resolve through it
        top_set={_SPLIT_PE},
        pe_by_slug={_SPLIT_SCN: _SPLIT_PE, "3010-OPN": _SPLIT_PE},
    )

    assert result["written"] == 1
    assert result["retired"] == []
    out = json.loads((json_dir / "dossiers" / f"{_SPLIT_SCN}.json").read_text())
    # pe_bli keeps meaning the program key; slug is the page identity
    assert out["pe_bli"] == _SPLIT_PE
    assert out["slug"] == _SPLIT_SCN
    assert out["dossier"]["what_it_is"]["claims"][0]["text"] == (
        "The member's own dossier."
    )


def test_a_page_keyed_archive_supersedes_the_bare_coded_one_for_that_page(
    tmp_path,
):
    """Both archives exist the moment one member is regenerated at its own
    key. The page-keyed one wins regardless of filename sort order, and the
    superseded archive is kept on disk."""
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, _SPLIT_PE, _clean("The OLD fused dossier."))
    _write_raw(raw_dir, _SPLIT_SCN, _clean("The NEW member dossier."))
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
        top_set={_SPLIT_PE},
        slug_by_pe={_SPLIT_PE: _SPLIT_SCN},
        pe_by_slug={_SPLIT_SCN: _SPLIT_PE, "3010-OPN": _SPLIT_PE},
    )

    assert result["written"] == 1
    out = json.loads((json_dir / "dossiers" / f"{_SPLIT_SCN}.json").read_text())
    assert out["dossier"]["what_it_is"]["claims"][0]["text"] == (
        "The NEW member dossier."
    )
    # paid research is never deleted
    assert (raw_dir / f"{_SPLIT_PE}.json").exists()
    assert (raw_dir / f"{_SPLIT_SCN}.json").exists()


def test_a_page_outside_the_top_set_is_still_retired(tmp_path):
    """The membership test moved to the page's CODE — it did not go away."""
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, _SPLIT_SCN, _clean())
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
        top_set={"SOMETHINGELSE"},
        pe_by_slug={_SPLIT_SCN: _SPLIT_PE},
    )

    assert result["written"] == 0
    assert result["retired"] == [_SPLIT_PE]
    assert not (json_dir / "dossiers" / f"{_SPLIT_SCN}.json").exists()


def test_an_ordinary_archive_is_unchanged_by_the_page_index(tmp_path):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "0601101E", _clean())
    json_dir = tmp_path / "json"

    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT},
        snapshot_urls=set(),
        top_set={"0601101E"},
        pe_by_slug={"0601101E": "0601101E", _SPLIT_SCN: _SPLIT_PE},
    )

    assert result["written"] == 1
    out = json.loads((json_dir / "dossiers" / "0601101E.json").read_text())
    assert out["pe_bli"] == "0601101E" and out["slug"] == "0601101E"
