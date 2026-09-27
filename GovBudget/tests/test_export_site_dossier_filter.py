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


# ---------------------------------------------------------------------------
# Ruling R-DEC-DOSSIERDRIFT (controller, 2026-09-26): a claim whose stated
# figure, concentration word or top-family name contradicts its cited fact's
# CURRENT value is WITHHELD at export — dropped from the published dossier,
# never rewritten — logged by name, and recorded on the sidecar so the page's
# Correction note counts it and the dossier gate's emptied-section exception
# can see why a section emptied.
#
# The shape is /program/0602025E/ at chain G, verbatim: its players claims
# cite the all-links concentration facts, whose values moved from what the
# sentences state (HHI 389 -> 1,284.683; $4.68B -> $469,988,662.80; RAYTHEON
# -> SYSTEM HIGH), and one lobbying claim whose citation no longer resolves.
# ---------------------------------------------------------------------------

_HHI_FID = "b45aa52df18b0f7c"
_DOLLARS_FID = "5a3b8a1cba0a8bbe"
_LOBBY_FID = "0e6a0c0b283d90d5"
_C_RAYTHEON = (
    "Across the program's award history, the leading recipient family by dollars"
    " is RAYTHEON, measured over roughly $4.68 billion in program dollars."
)
_C_389 = (
    "Award dollars are spread across 189 recipient families, producing a low"
    " concentration score (Herfindahl-Hirschman Index of about 389), which"
    " indicates a relatively diverse contractor base overall."
)
_C_INDYNE = (
    "The largest single tracked award, worth about $210.1 million, went to"
    " INDYNE, INC. (contract FA251718C8000, Alaska)."
)


def _drift_export(tmp_path, players, *, concentration=True):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(
        raw_dir,
        "0602025E",
        _sections(
            what_it_is=[_claim("It is a DARPA applied research program.", fact_id=GOOD_FACT)],
            why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
            players=players,
        ),
    )
    json_dir = tmp_path / "json"
    result = _emit_dossier_sidecars(
        json_dir=json_dir,
        dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _HHI_FID, _DOLLARS_FID},
        snapshot_urls=set(),
        fact_id_to_recorded_value={_HHI_FID: "1284.683", _DOLLARS_FID: "469988662.800"},
        citation_facts={
            _HHI_FID: {"kind": "derived", "units": "Herfindahl-Hirschman Index",
                       "recorded_value": "1284.683"},
            _DOLLARS_FID: {"kind": "derived", "units": "USD",
                           "recorded_value": "469988662.800"},
        },
        concentration_facts=(
            {fid: {"family_key": "SYSTEM HIGH", "display_name": "SYSTEM HIGH CORPORATION",
                   "hhi": 1284.683} for fid in (_HHI_FID, _DOLLARS_FID)}
            if concentration else None
        ),
    )
    out = json.loads((json_dir / "dossiers" / "0602025E.json").read_text())
    return result, out


def test_contradicting_claims_are_withheld_and_logged_by_name(tmp_path, capsys):
    result, out = _drift_export(tmp_path, [
        _claim(_C_RAYTHEON, fact_id=_DOLLARS_FID),
        _claim(_C_389, fact_id=_HHI_FID),
        _claim(_C_INDYNE, fact_id=_DOLLARS_FID),
        _claim("Lockheed Martin lobbied on supply chains.", fact_id=_LOBBY_FID),
    ])

    # Withheld, not rewritten: players emptied, nothing else touched.
    assert out["dossier"]["players"]["claims"] == []
    assert len(out["dossier"]["what_it_is"]["claims"]) == 1
    assert out["dropped_claims"] == 4
    assert out["dropped_claims_by_section"] == {"players": 4}
    assert out["dropped_reasons"] == {"contradicts_citation": 3, "unresolvable_citation": 1}

    withheld = out["withheld_claims"]
    assert [w["text"] for w in withheld] == [_C_RAYTHEON, _C_389, _C_INDYNE]
    assert withheld[0] == {
        "section": "players", "claim": 0, "text": _C_RAYTHEON,
        "fact_id": _DOLLARS_FID, "kind": "derived", "units": "USD",
        "cited_value": "469988662.800", "cited_family": "SYSTEM HIGH",
        "reasons": ["stated_figure", "top_family"], "unlinked_recipients": [],
        "unlisted_lobbying_filers": [],
    }
    assert withheld[1]["reasons"] == ["stated_figure", "concentration_band"]
    assert withheld[1]["cited_value"] == "1284.683"
    assert withheld[2]["reasons"] == ["stated_figure"]

    assert result["withheld_by_pe"] == {"0602025E": 3}
    assert result["total_withheld"] == 3
    assert result["dropped_by_pe"] == {"0602025E": 4}
    log = capsys.readouterr().out
    assert "withheld" in log and "0602025E players[1]" in log
    assert "Herfindahl-Hirschman Index of about 389" in log and "1284.683" in log


def test_a_true_claim_on_the_same_fact_is_kept(tmp_path):
    true_claim = _claim(
        "The leading recipient family is SYSTEM HIGH, over about $470.0 million in"
        " program dollars; the field is moderately concentrated.",
        fact_id=_DOLLARS_FID,
    )
    _result, out = _drift_export(tmp_path, [true_claim, _claim(_C_389, fact_id=_HHI_FID)])
    assert out["dossier"]["players"]["claims"] == [true_claim]
    assert out["dropped_reasons"] == {"contradicts_citation": 1}
    assert [w["claim"] for w in out["withheld_claims"]] == [1]


def test_the_figure_check_runs_without_the_concentration_index(tmp_path):
    """The family check needs the mart; the figure and band checks need only
    the citation row — so a missing index withholds on those alone."""
    _result, out = _drift_export(
        tmp_path, [_claim(_C_RAYTHEON, fact_id=_DOLLARS_FID)], concentration=False)
    assert out["withheld_claims"][0]["reasons"] == ["stated_figure"]


def test_a_legacy_caller_without_units_withholds_nothing_new(tmp_path):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "0602025E", _sections(
        what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
        why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
        players=[_claim(_C_389, fact_id=_HHI_FID)],
    ))
    json_dir = tmp_path / "json"
    result = _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _HHI_FID}, snapshot_urls=set(),
    )
    out = json.loads((json_dir / "dossiers" / "0602025E.json").read_text())
    assert out["withheld_claims"] == []
    assert result["total_withheld"] == 0


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERDRIFT round 2 (2026-09-26): any fact kind, recipient lists,
# and a drift context that fails closed.
# ---------------------------------------------------------------------------

_WB_FID = "6ce1109572aa7881"   # 0607210D8Z R-1 J1074, FY2024 actuals
_PROG_DOLLARS_FID = "3b594c81c720df35"   # 0603467E program dollars
_C_0607210D8Z = (
    "The FY 2026 request includes $273.379 million of discretionary funding and"
    " $2,054.991 million of mandatory (reconciliation) funding, for a total of"
    " $2,328.370 billion."
)
_C_RECIPIENTS = (
    "Recorded recipients of awards linked to the program include Booz Allen"
    " Hamilton, The Johns Hopkins University Applied Physics Laboratory, Leidos,"
    " Raytheon Company, Lockheed Martin Corporation, Northrop Grumman Systems"
    " Corp, SRI International, and the Massachusetts Institute of Technology."
)
_LINKS_0603467E = [
    ("RAYTHEON COMPANY", "RAYTHEON", "RAYTHEON COMPANY"),
    ("NORTHROP GRUMMAN SYSTEMS CORP", "NORTHROP GRUMMAN", "NORTHROP GRUMMAN CORPORATION"),
    ("APPLIED PHYSICAL SCIENCES CORP", "GENERAL DYNAMICS", "GENERAL DYNAMICS CORP"),
    ("SYSTEM HIGH CORPORATION", "SYSTEM HIGH", "SYSTEM HIGH CORPORATION"),
]


def _round2_export(tmp_path, pe, sections, **kw):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, pe, sections)
    json_dir = tmp_path / "json"
    result = _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _WB_FID, _PROG_DOLLARS_FID}, snapshot_urls=set(),
        **kw,
    )
    return result, json.loads((json_dir / "dossiers" / f"{pe}.json").read_text())


def test_a_workbook_claim_contradicting_its_cell_is_withheld(tmp_path, capsys):
    """/program/0607210D8Z/ what_it_is[4]: "$2,328.370 billion" and two
    parts, none within the sentence's rounding of the cited R-1 cell
    (897,631 thousand) — round 1 read recorded_value only and kept it."""
    kept = _claim("The program sits in Budget Activity 7.", fact_id=GOOD_FACT)
    result, out = _round2_export(
        tmp_path, "0607210D8Z",
        _sections(what_it_is=[kept, _claim(_C_0607210D8Z, fact_id=_WB_FID)],
                  why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
                  players=[_claim("It has players.", fact_id=GOOD_FACT)]),
        citation_facts={_WB_FID: {"kind": "workbook", "units": "USD thousands",
                                  "amount_text": None, "amount_thousands": 897631.0,
                                  "recorded_value": None}},
    )
    assert out["dossier"]["what_it_is"]["claims"] == [kept]
    assert out["dropped_reasons"] == {"contradicts_citation": 1}
    [w] = out["withheld_claims"]
    assert w["kind"] == "workbook" and w["units"] == "USD thousands"
    assert w["cited_value"] == 897631.0 and w["reasons"] == ["stated_figure"]
    assert result["withheld_by_pe"] == {"0607210D8Z": 1}
    assert "$2,328.370 billion" in capsys.readouterr().out


def test_a_recipient_list_naming_unlinked_recipients_is_withheld(tmp_path, capsys):
    """/program/0603467E/ players[3]: 6 of its 8 named recipients are not
    among the page's linked-award recipient families."""
    from govbudget.dossiers.claim_drift import RecipientIndex

    kept = _claim("The top recipient family is General Dynamics.", fact_id=GOOD_FACT)
    result, out = _round2_export(
        tmp_path, "0603467E",
        _sections(what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
                  why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
                  players=[kept, _claim(_C_RECIPIENTS, fact_id=_PROG_DOLLARS_FID)]),
        fact_id_to_recorded_value={_PROG_DOLLARS_FID: "74376328.830"},
        citation_facts={_PROG_DOLLARS_FID: {"kind": "derived", "units": "USD",
                                            "recorded_value": "74376328.830"}},
        linked_recipients=RecipientIndex({"0603467E": _LINKS_0603467E}, {}),
    )
    assert out["dossier"]["players"]["claims"] == [kept]
    assert out["dropped_reasons"] == {"contradicts_citation": 1}
    [w] = out["withheld_claims"]
    assert w["reasons"] == ["recipient_list"]
    assert w["unlinked_recipients"] == [
        "Booz Allen Hamilton", "The Johns Hopkins University Applied Physics Laboratory",
        "Leidos", "Lockheed Martin Corporation", "SRI International",
        "the Massachusetts Institute of Technology",
    ]
    log = capsys.readouterr().out
    assert "0603467E players[1]" in log and "unlinked: Booz Allen Hamilton" in log


def test_a_list_whose_names_are_all_linked_is_kept(tmp_path):
    from govbudget.dossiers.claim_drift import RecipientIndex

    claim = _claim("Recorded recipients of awards linked to the program include Raytheon"
                   " Company and Northrop Grumman Systems Corp.", fact_id=GOOD_FACT)
    _result, out = _round2_export(
        tmp_path, "0603467E",
        _sections(what_it_is=[_claim("A thing.", fact_id=GOOD_FACT)],
                  why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
                  players=[claim]),
        linked_recipients=RecipientIndex({"0603467E": _LINKS_0603467E}, {}),
    )
    assert out["dossier"]["players"]["claims"] == [claim]
    assert out["withheld_claims"] == []


def test_the_recipient_check_is_keyed_by_the_page_not_the_bare_code(tmp_path):
    """A split archive lands on its member PAGE ("3010-SCN"); the linked set
    is that page's, never the sibling's."""
    from govbudget.dossiers.claim_drift import RecipientIndex

    claim = _claim("Huntington Ingalls Incorporated is a recipient linked to this budget"
                   " line through contract records.", fact_id=GOOD_FACT)
    index = RecipientIndex(
        {"3010-OPN": [("HUNTINGTON INGALLS INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES",
                       None)]}, {})
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "3010", _sections(
        what_it_is=[_claim("A ship.", fact_id=GOOD_FACT)],
        why_it_matters=[_claim("Matters.", fact_id=GOOD_FACT)],
        players=[claim]))
    json_dir = tmp_path / "json"
    _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir, citations_keyset={GOOD_FACT},
        snapshot_urls=set(), slug_by_pe={"3010": "3010-SCN"}, linked_recipients=index)
    out = json.loads((json_dir / "dossiers" / "3010-SCN.json").read_text())
    assert out["dossier"]["players"]["claims"] == []
    assert out["withheld_claims"][0]["reasons"] == ["recipient_list"]


def test_the_drift_context_reads_every_value_kind(tmp_path):
    from govbudget.export_site import _dossier_drift_context

    def row(fid, kind, units, amount_text=None, amount_thousands=None, recorded=None):
        r = [None] * 27
        r[0], r[1], r[2], r[3], r[14], r[23] = (
            fid, kind, units, amount_text, amount_thousands, recorded)
        return tuple(r)

    facts, conc, recipients, lobbying = _dossier_drift_context(
        [row("w", "workbook", "USD thousands", amount_thousands=897631.0),
         row("p", "jbook_pdf", "USD millions", amount_text="7,712.804"),
         row("d", "derived", "USD", recorded="1.0"),
         row("n", "jbook_narrative", None),
         row("l", "lda_filing", None)],
        None,
    )
    assert facts["w"]["amount_thousands"] == 897631.0 and facts["w"]["kind"] == "workbook"
    assert facts["p"]["amount_text"] == "7,712.804" and facts["p"]["units"] == "USD millions"
    assert facts["d"]["recorded_value"] == "1.0"
    assert "n" not in facts  # no value to compare
    # R-DEC-DOSSIERLDA: an LDA mention row carries no value, but its KIND
    # makes a claim citing it a lobbying claim ("Additional FedEx Corporation
    # filings in 2024 referenced …" says no "lobby…" word of its own)
    assert facts["l"]["kind"] == "lda_filing"
    assert conc == {} and recipients is None and lobbying is None


def test_the_drift_context_fails_closed_on_an_unreadable_mart(tmp_path, capsys):
    """A supplied mart that cannot be read STOPS the export (never an empty
    index, which would silently skip the family and recipient legs)."""
    import pytest

    from govbudget.dossiers.claim_drift import ClaimDriftIndexError
    from govbudget.export_site import _dossier_drift_context

    with pytest.raises(ClaimDriftIndexError):
        _dossier_drift_context([], tmp_path / "absent.duckdb")
    assert "export-site: ERROR" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERDRIFT round 3 (2026-09-26): fiscal-year label agreement, and a
# Correction note that is true for every drop its reason covers.
# ---------------------------------------------------------------------------

_JB_FY2025_FID = "ef8d1da3e605d4f0"   # 1203154SF, glyph 243.282 under "FY 2025"
_C_1203154SF = (
    "For FY2026, the Auxiliary Payloads project is funded at about $243.3"
    " million (its Current Year amount), making it the dominant project within"
    " the program."
)


def test_the_drift_context_carries_each_facts_column(tmp_path):
    from govbudget.export_site import _dossier_drift_context

    def row(fid, kind, units, amount_text=None, amount_thousands=None, scenario=None,
            amount_type=None):
        r = [None] * 27
        r[0], r[1], r[2], r[3], r[14], r[25], r[26] = (
            fid, kind, units, amount_text, amount_thousands, scenario, amount_type)
        return tuple(r)

    facts, _conc, _rec, _lob = _dossier_drift_context(
        [row("p", "jbook_pdf", "USD millions", amount_text="243.282", scenario="CurrentYear"),
         row("w", "workbook", "USD thousands", amount_thousands=1.0,
             amount_type="fy_2025_enacted")],
        None,
    )
    assert facts["p"]["scenario"] == "CurrentYear" and facts["p"]["amount_type"] is None
    assert facts["w"]["amount_type"] == "fy_2025_enacted" and facts["w"]["scenario"] is None


def test_a_claim_naming_another_fiscal_year_than_its_column_is_withheld(tmp_path, capsys):
    kept = _claim("The program is a Space Force research line.", fact_id=GOOD_FACT)
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "1203154SF", _sections(
        what_it_is=[kept, _claim(_C_1203154SF, fact_id=_JB_FY2025_FID)],
        why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
        players=[_claim("It has players.", fact_id=GOOD_FACT)]))
    json_dir = tmp_path / "json"
    fact = {"kind": "jbook_pdf", "units": "USD millions", "amount_text": "243.282",
            "amount_thousands": None, "recorded_value": None,
            "scenario": "CurrentYear", "amount_type": None}
    result = _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _JB_FY2025_FID}, snapshot_urls=set(),
        citation_facts={_JB_FY2025_FID: fact})
    out = json.loads((json_dir / "dossiers" / "1203154SF.json").read_text())
    assert out["dossier"]["what_it_is"]["claims"] == [kept]
    assert out["dropped_reasons"] == {"contradicts_citation": 1}
    [w] = out["withheld_claims"]
    assert w["reasons"] == ["fiscal_year"] and w["cited_value"] == "243.282"
    assert result["withheld_by_pe"] == {"1203154SF": 1}
    assert "1203154SF what_it_is[1]" in capsys.readouterr().out

    # the same sentence, labelled with its column's year, is kept
    _write_raw(raw_dir, "1203154SF", _sections(
        what_it_is=[_claim(_C_1203154SF.replace("FY2026", "FY2025"),
                           fact_id=_JB_FY2025_FID)],
        why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
        players=[_claim("It has players.", fact_id=GOOD_FACT)]))
    _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _JB_FY2025_FID}, snapshot_urls=set(),
        citation_facts={_JB_FY2025_FID: fact})
    out = json.loads((json_dir / "dossiers" / "1203154SF.json").read_text())
    assert out["withheld_claims"] == [] and out["dropped_claims"] == 0


def test_the_unresolvable_citation_note_is_true_of_a_non_lobbying_drop(tmp_path):
    """/program/1000/ at chain G: 5 J-book narrative claims whose facts no
    longer resolve — the note used to call them "lobbying mentions". The
    exporter's unresolvable_citation reason covers ANY citation that does not
    resolve (a fact_id not in citations.json, a url with no cached snapshot,
    a malformed citation), so its clause names no one kind of source."""
    from govbudget.dossiers.gate import expected_correction_note

    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "1000", _sections(
        what_it_is=[_claim("The line funds private contracted ship maintenance for the"
                           " U.S. Pacific Fleet.", fact_id="30748db80a2d678e"),
                    _claim("A thing.", fact_id=GOOD_FACT)],
        why_it_matters=[_claim("It matters.", url="https://example.com/not-cached")],
        players=[_claim("It has players.", fact_id=GOOD_FACT)]))
    json_dir = tmp_path / "json"
    _emit_dossier_sidecars(json_dir=json_dir, dossiers_raw_dir=raw_dir,
                           citations_keyset={GOOD_FACT}, snapshot_urls=set())
    out = json.loads((json_dir / "dossiers" / "1000.json").read_text())
    assert out["dropped_reasons"] == {"unresolvable_citation": 2}
    note = expected_correction_note(out["dropped_claims"], out["dropped_reasons"])
    assert note == "2 claims removed: they cited sources the site could not resolve."
    assert "lobbying" not in note


def test_a_fiscal_year_withhold_is_named_in_the_correction_note(tmp_path):
    """The contradicts_citation clause must be true of each of its sub-reasons.
    /program/1203154SF/ what_it_is[3] is withheld for its fiscal year alone —
    its figure agrees with the cited glyph — so a note saying it "stated a
    figure or recipient its sources do not support" named neither thing
    actually wrong with it (round 4)."""
    from govbudget.dossiers.gate import expected_correction_note

    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "1203154SF", _sections(
        what_it_is=[_claim(_C_1203154SF, fact_id=_JB_FY2025_FID)],
        why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
        players=[_claim("It has players.", fact_id=GOOD_FACT)]))
    json_dir = tmp_path / "json"
    _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _JB_FY2025_FID}, snapshot_urls=set(),
        citation_facts={_JB_FY2025_FID: {
            "kind": "jbook_pdf", "units": "USD millions", "amount_text": "243.282",
            "amount_thousands": None, "recorded_value": None,
            "scenario": "CurrentYear", "amount_type": None}})
    out = json.loads((json_dir / "dossiers" / "1203154SF.json").read_text())
    assert [w["reasons"] for w in out["withheld_claims"]] == [["fiscal_year"]]
    assert expected_correction_note(out["dropped_claims"], out["dropped_reasons"]) == (
        "1 claim removed: it stated a figure, year, recipient or lobbying filer its"
        " sources do not support.")


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERLDA (final-review ruling, 2026-09-27): a claim naming a
# lobbying filer the page's lobbying mentions do not list is withheld under
# contradicts_citation, sub-reason lobbying_mention, and the Correction note's
# clause names what was wrong with it ("lobbying filer" — FedEx is no
# recipient of the page's awards).
# ---------------------------------------------------------------------------

_LDA_FEDEX_821800 = "0823104dbb624904"   # a FedEx mention of 821800
_LDA_FEDEX_0208085JCY = "019440805ba04bc0"   # a FedEx mention of 0208085JCY
_LDA_GD_FILING = "2e0033079e665cda"   # a General Dynamics filing's amount
_C_2004_FEDEX = (
    "Additional FedEx Corporation filings in 2024 referenced legislative"
    " monitoring of Open Skies Agreements and general trade issues including"
    " customs modernization."
)
_C_1045_FEDEX = (
    "A FedEx Corporation filing matched the term '1045' while describing lobbying"
    " on aviation security and safety issues — a coincidental keyword match"
    " unrelated to the submarine program (2026 filing)."
)
_C_1045_GD = (
    "Lobbying filings from General Dynamics Corporation reported lobbying for full"
    " funding of the Virginia Class and Columbia Class submarine programs and"
    " funding for the submarine industrial base (2026 filing)."
)
_LDA_FACTS = {
    _LDA_FEDEX_821800: {"kind": "lda_filing", "units": None},
    _LDA_FEDEX_0208085JCY: {"kind": "lda_filing", "units": None},
    _LDA_GD_FILING: {"kind": "lda_filing", "units": "USD", "recorded_value": "37500"},
}


def _lobbying_index():
    from govbudget.dossiers.claim_drift import FilerUniverse, LobbyingIndex

    universe = FilerUniverse.from_filings([
        ("FEDEX CORPORATION", "FEDEX CORPORATION", "FEDEX"),
        ("GENERAL DYNAMICS CORPORATION", "MELTSNER STRATEGIES, LLC", "GENERAL DYNAMICS"),
        ("HUNTINGTON INGALLS INDUSTRIES INCORPORATED",
         "HUNTINGTON INGALLS INDUSTRIES INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES"),
    ])
    return LobbyingIndex({
        # 2004 lists no mention after the #176 rematch
        "1045": [("GENERAL DYNAMICS CORPORATION", "GENERAL DYNAMICS",
                  "MELTSNER STRATEGIES, LLC"),
                 ("HUNTINGTON INGALLS INDUSTRIES INCORPORATED",
                  "HUNTINGTON INGALLS INDUSTRIES",
                  "HUNTINGTON INGALLS INDUSTRIES INCORPORATED")],
    }, universe)


def _lda_export(tmp_path, pe, players):
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, pe, _sections(
        what_it_is=[_claim("An aircraft carrier.", fact_id=GOOD_FACT)],
        why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
        players=players))
    json_dir = tmp_path / "json"
    result = _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, *_LDA_FACTS}, snapshot_urls=set(),
        fact_id_to_recorded_value={_LDA_GD_FILING: "37500"},
        citation_facts=_LDA_FACTS, lobbying_mentions=_lobbying_index())
    return result, json.loads((json_dir / "dossiers" / f"{pe}.json").read_text())


def test_2004_fedex_key_player_claim_is_withheld_and_logged(tmp_path, capsys):
    from govbudget.dossiers.gate import expected_correction_note

    navy = _claim("The program is managed by the Navy (organization code N).",
                  fact_id=GOOD_FACT)
    result, out = _lda_export(tmp_path, "2004", [
        navy, _claim(_C_2004_FEDEX, fact_id=_LDA_FEDEX_821800)])
    assert out["dossier"]["players"]["claims"] == [navy]
    assert out["dropped_reasons"] == {"contradicts_citation": 1}
    [w] = out["withheld_claims"]
    assert w["reasons"] == ["lobbying_mention"] and w["kind"] == "lda_filing"
    assert w["unlisted_lobbying_filers"] == ["FedEx Corporation"]
    assert w["unlinked_recipients"] == []
    assert result["withheld_by_pe"] == {"2004": 1}
    log = capsys.readouterr().out
    assert "2004 players[1]" in log
    assert "unlisted lobbying filers: FedEx Corporation" in log
    assert expected_correction_note(out["dropped_claims"], out["dropped_reasons"]) == (
        "1 claim removed: it stated a figure, year, recipient or lobbying filer its"
        " sources do not support.")


def test_1045_fedex_claim_is_withheld_and_a_listed_filers_claim_kept(tmp_path):
    gd = _claim(_C_1045_GD, fact_id=_LDA_GD_FILING)
    _result, out = _lda_export(tmp_path, "1045", [
        gd, _claim(_C_1045_FEDEX, fact_id=_LDA_FEDEX_0208085JCY)])
    assert out["dossier"]["players"]["claims"] == [gd]
    assert [w["unlisted_lobbying_filers"] for w in out["withheld_claims"]] == [
        ["FedEx Corporation"]]


def test_without_a_lobbying_index_no_lobbying_claim_is_withheld(tmp_path):
    """A legacy caller (no lobbying_mentions) runs no lobbying leg."""
    raw_dir = tmp_path / "dossiers-raw"
    fedex = _claim(_C_2004_FEDEX, fact_id=_LDA_FEDEX_821800)
    _write_raw(raw_dir, "2004", _sections(
        what_it_is=[_claim("A carrier.", fact_id=GOOD_FACT)],
        why_it_matters=[_claim("It matters.", fact_id=GOOD_FACT)],
        players=[fedex]))
    json_dir = tmp_path / "json"
    _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _LDA_FEDEX_821800}, snapshot_urls=set(),
        citation_facts=_LDA_FACTS)
    out = json.loads((json_dir / "dossiers" / "2004.json").read_text())
    assert out["dossier"]["players"]["claims"] == [fedex]


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERDRIFT round 4 (2026-09-26): the #56 stale_value check reads
# every figure the sentence states, not only its "$X thousand" ones.
#
# /program/2122/ why_it_matters[6], verbatim, cites 8169f40c26f22ffd, a
# derived fact in USD thousands whose recorded_value is 1,883,217.000
# (= 6,366,431 - 4,483,214). Its headline "$1.9 billion" is that value within
# the rounding the sentence prints (+/- $0.05 billion); its two "$X thousand"
# figures are the formula's inputs. The check read only the inputs, withheld a
# true claim as stale_value, and the page's note said "it stated a figure a
# later correction changed" — false.
# ---------------------------------------------------------------------------

_FID_2122 = "8169f40c26f22ffd"
_C_2122 = (
    "DDG-51 FY2024 actuals came in about $1.9 billion above the original PB2024"
    " request, rising from a $4,483,214 thousand request to $6,366,431 thousand in"
    " actuals — a roughly 42% increase."
)
#: the #56 collision shape _claim_value_still_matches was written for: one
#: stated figure, no other number to fall back on, a re-keyed fact now 20,900
_FID_3010 = "21956c874a3b2de1"
_C_3010_STALE = (
    "The program's total FY2026 funding across both accounts is $2,620,900 thousand."
)


def test_a_true_headline_figure_keeps_the_claim():
    from govbudget.export_site import _claim_value_still_matches

    assert _claim_value_still_matches(_C_2122, "1883217.000", "USD thousands")
    # a legacy caller passes no units: the check's own "$X thousand"
    # convention (recorded_value in USD thousands) applies
    assert _claim_value_still_matches(_C_2122, "1883217.000")
    # the same value recorded in whole dollars
    assert _claim_value_still_matches(_C_2122, "1883217000.000", "USD")
    # the edge of the sentence's own rounding: $1.9 billion is 1.85-1.95
    assert _claim_value_still_matches(_C_2122, "1949000.000", "USD thousands")


def test_a_claim_whose_figures_all_disagree_is_still_stale():
    from govbudget.export_site import _claim_value_still_matches

    assert not _claim_value_still_matches(_C_3010_STALE, "20900.000", "USD thousands")
    assert not _claim_value_still_matches(_C_3010_STALE, "20900.000")
    # a headline outside its own rounding does not rescue the claim:
    # $1.9 billion vs $1.983 billion, and neither input is the value
    assert not _claim_value_still_matches(_C_2122, "1983217.000", "USD thousands")
    # a headline that disagrees as well
    assert not _claim_value_still_matches(
        "The program's total FY2026 funding is about $2.6 billion ($2,620,900"
        " thousand) across both accounts.", "20900.000", "USD thousands")
    # a fact whose units are not a dollar scale: no other-scale figure can be
    # compared, so the "$X thousand" verdict stands
    assert not _claim_value_still_matches(_C_2122, "1883217.000", "percent")


def test_the_2122_claim_is_published_and_a_stale_one_still_withheld(tmp_path):
    from govbudget.dossiers.gate import expected_correction_note

    def derived(value):
        return {"kind": "derived", "units": "USD thousands", "recorded_value": value,
                "amount_text": None, "amount_thousands": None,
                "scenario": None, "amount_type": None}

    true_claim = _claim(_C_2122, fact_id=_FID_2122)
    raw_dir = tmp_path / "dossiers-raw"
    _write_raw(raw_dir, "2122", _sections(
        what_it_is=[_claim("It buys DDG-51 destroyers.", fact_id=GOOD_FACT),
                    _claim(_C_3010_STALE, fact_id=_FID_3010)],
        why_it_matters=[true_claim],
        players=[_claim("It has players.", fact_id=GOOD_FACT)]))
    json_dir = tmp_path / "json"
    result = _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _FID_2122, _FID_3010}, snapshot_urls=set(),
        fact_id_to_recorded_value={_FID_2122: "1883217.000", _FID_3010: "20900.000"},
        citation_facts={_FID_2122: derived("1883217.000"), _FID_3010: derived("20900.000")})
    out = json.loads((json_dir / "dossiers" / "2122.json").read_text())
    assert out["dossier"]["why_it_matters"]["claims"] == [true_claim]
    assert [c["text"] for c in out["dossier"]["what_it_is"]["claims"]] == [
        "It buys DDG-51 destroyers."]
    assert out["dropped_claims"] == 1
    assert out["dropped_reasons"] == {"stale_value": 1}
    assert out["withheld_claims"] == []
    assert result["dropped_by_pe"] == {"2122": 1}
    assert expected_correction_note(out["dropped_claims"], out["dropped_reasons"]) == (
        "1 claim removed: it stated a figure a later correction changed.")

    # a legacy caller (no citation_facts, so no units) keeps it too
    _emit_dossier_sidecars(
        json_dir=json_dir, dossiers_raw_dir=raw_dir,
        citations_keyset={GOOD_FACT, _FID_2122, _FID_3010}, snapshot_urls=set(),
        fact_id_to_recorded_value={_FID_2122: "1883217.000", _FID_3010: "20900.000"})
    out = json.loads((json_dir / "dossiers" / "2122.json").read_text())
    assert out["dossier"]["why_it_matters"]["claims"] == [true_claim]
    assert out["dropped_reasons"] == {"stale_value": 1}


def test_the_drift_context_reads_the_lobbying_index_and_fails_closed(tmp_path, capsys):
    """_dossier_drift_context builds the lobbying index from the same mart as
    the other legs, and a mart without the lobbying relations STOPS the
    export (never an empty index, which would publish every FedEx claim)."""
    import duckdb
    import pytest

    from govbudget.dossiers.claim_drift import ClaimDriftIndexError, LobbyingIndex
    from govbudget.export_site import _dossier_drift_context

    db = tmp_path / "m.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table fct_program_concentration (pe_bli varchar, hhi_all double,"
                " top_family_all varchar, hhi_high double, top_family_high varchar)")
    con.execute("create table dim_entities (family_key varchar, display_name varchar)")
    con.execute("create table dim_programs (pe_bli varchar, account varchar,"
                " account_title varchar, org varchar, exhibit_family varchar)")
    con.execute("create table fct_budget_to_awards (pe_bli varchar, account varchar,"
                " organization varchar, award_piid varchar, recipient_name varchar,"
                " recipient_uei varchar)")
    con.execute("create table entity_xwalk (recipient_uei varchar, recipient_name varchar,"
                " parent_name varchar, family_key varchar)")
    con.close()
    with pytest.raises(ClaimDriftIndexError, match="audit_lda_filings"):
        _dossier_drift_context([], db)
    assert "export-site: ERROR" in capsys.readouterr().out

    con = duckdb.connect(str(db))
    con.execute("create table fct_program_lobbying (filing_uuid varchar, pe_bli varchar,"
                " client_name varchar, family_key varchar)")
    con.execute("create table audit_lda_filings (filing_uuid varchar, client_name varchar,"
                " registrant_name varchar, family_key_guess varchar, match_method varchar)")
    con.execute("insert into audit_lda_filings values ('f', 'FEDEX CORPORATION',"
                " 'FEDEX CORPORATION', 'FEDEX', 'exact_family')")
    con.close()
    _facts, _conc, _rec, lobbying = _dossier_drift_context([], db)
    assert isinstance(lobbying, LobbyingIndex)
    assert lobbying.for_page("2004").names == frozenset()
