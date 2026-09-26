"""Phase 5B-3 Task 7b tests: dossier batch pipeline + cited-or-absent gate.

Fully mocked — no network, no ANTHROPIC_API_KEY (plan decision 6). Coverage:
  - DOSSIER_SCHEMA shape (cited-or-absent, additionalProperties false)
  - bundle building (narratives full, top-25 caps, trajectory fact_ids,
    pe-scoped feed events, flows summary, category row, snapshots) + token
    trimming (prefix-of-stages invariant, hard cap guarantee)
  - heuristic vs count_tokens token counting
  - estimator math at Batch rates ($2.50/$12.50 per MTok, full max_tokens out)
  - submit: blocked-on-no-key SystemExit, cost-cap abort (no batch created),
    happy path (requests shape per recon §G, batch_meta.json persisted)
  - collect: poll-until-ended, raw archive, parsed dossier output, errored +
    schema-invalid items listed loudly
  - gate: pass case, unresolvable fact_id/url, <80% warehouse ratio, empty
    required section, missing dossier file, category coverage + source_ref
    resolvability, pre-batch dim_programs assertion
"""
from __future__ import annotations

import json
import math
import re

from govbudget.dossiers import batch
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from govbudget.dossiers.batch import (
    ALL_SECTIONS,
    BATCH_INPUT_USD_PER_MTOK,
    BATCH_OUTPUT_USD_PER_MTOK,
    BUNDLE_TOKEN_CAP,
    DOSSIER_SCHEMA,
    MAX_OUTPUT_TOKENS,
    MODEL,
    REQUIRED_SECTIONS,
    SHARED_PREAMBLE,
    _TRIM_STAGES,
    _lda_url_to_fact_id,
    _load_citations_keyset,
    build_bundle,
    build_requests,
    collect,
    estimate_cost,
    heuristic_token_count,
    make_token_counter,
    require_client,
    submit,
    validate_dossier,
)
from govbudget.dossiers import gate as gate_module
from govbudget.dossiers.gate import (
    dossier_gate,
    pre_batch_check,
    source_ref_resolvable,
)

PE = "0601101E"
PE2 = "0603183D8Z"
SHA = "ab" * 32
SNAP_URL = "https://example.com/article"


# ---------------------------------------------------------------------------
# Fixtures: sidecars + snapshots + categories + duckdb
# ---------------------------------------------------------------------------


@pytest.fixture()
def site_fixture(tmp_path):
    """tmp data layout mirroring data/site/json + data/research/snapshots."""
    site_json = tmp_path / "site" / "json"
    (site_json / "program_details").mkdir(parents=True)
    (site_json / "flows").mkdir()
    snapshots = tmp_path / "research" / "snapshots"
    snapshots.mkdir(parents=True)

    (site_json / "programs.json").write_text(json.dumps([
        {
            "pe_bli": PE, "title": "Defense Research Sciences", "org": "DARPA",
            "trajectory": {"fy2025_total": 50.0, "fy2026_total": 100.0},
            "trajectory_fact_ids": {"fy2026_total": "traj26fact",
                                    "fy2025_total": "traj25fact"},
            # #80 fix round 1: the high-only basis publishes here, so the
            # bundle carries it — and only it (batch._headline_concentration).
            # A block whose hhi_high is None reaches the prompt as no
            # concentration block at all; see
            # tests/test_export_site_5b3.py::TestConcentrationTwoBases.
            "hhi": {"hhi_all": 2500.0, "hhi_all_fact_id": "allhhifact",
                    "program_dollars_all": 5e8,
                    "program_dollars_all_fact_id": "alldollarsfact",
                    "top_family_all": "LOCKHEED MARTIN",
                    "family_count_all": 12, "award_count_all": 40,
                    "hhi_high": 3900.0, "hhi_high_fact_id": "hhifact",
                    "program_dollars_high": 3e8,
                    "program_dollars_high_fact_id": "dollarsfact",
                    "top_family_high": "BOEING",
                    "family_count_high": 4, "award_count_high": 9},
        },
        {"pe_bli": PE2, "title": "Joint Hypersonic Technology", "org": "OSD",
         "trajectory": {"fy2026_total": 500.0},
         "trajectory_fact_ids": {"fy2026_total": "traj26fact2"}},
    ]))

    (site_json / "program_details" / f"{PE}.json").write_text(json.dumps({
        "narratives": [
            # xml_path should be stripped from bundle (internal locator, not citable)
            {"kind": "mission", "title": "Mission", "body": "M" * 3000,
             "xml_path": "ProgramElement[0]/AccomplishmentPlannedProgram[0]"},
            {"kind": "accomplishments", "title": "Acc", "body": "A" * 3000,
             "xml_path": "ProgramElement[0]/AccomplishmentPlannedProgram[1]"},
        ],
        "mentions": [
            {"client_name": f"CLIENT {i}", "filing_uuid": f"uuid-{i}",
             "description_snippet": "lobbying on research",
             "filing_url": f"https://lda.senate.gov/api/v1/filings/uuid-{i}/"}
            for i in range(30)
        ],
        "awards": [
            {"award_piid": f"PIID{i}", "confidence": "high",
             "recipient_name": f"VENDOR {i}"}
            for i in range(30)
        ],
        "budget_lines": [
            {"fact_id": "blfact", "amount_thousands": 280494.0,
             "amount_type": "fy_2024_actuals", "organization": "DARPA"},
        ],
        # Mix: detfact0..4 will be in citations.json; detfact5..29 will NOT.
        # Also include rows WITHOUT a fact_id (xml_path-only) to ensure they
        # are handled gracefully.
        "details": [
            {"fact_id": f"detfact{i}", "project_title": f"PROJ {i}",
             "amount_millions": float(i), "xml_path": f"ProgramElement[0]/Project[{i}]"}
            for i in range(30)
        ],
    }))

    (site_json / "feed.json").write_text(json.dumps({"cards": [
        {"pe_bli": PE, "event_type": "yoy_swing", "figure_fact_id": "feedfact",
         "headline": "swing"},
        {"pe_bli": "0699OTHER", "event_type": "zeroed_fy2026",
         "figure_fact_id": "otherfact", "headline": "other"},
    ], "total": 2}))

    (site_json / "flows" / f"{PE}.json").write_text(json.dumps({"awards": [
        {"piid": f"F{i}", "dollars": 100.0, "family_slug": "indyne",
         "district": "AK-00", "confidence": "high"}
        for i in range(12)
    ]}))

    # citations.json: only detfact0..4 are present; detfact5..29 are absent.
    # Also includes lda_filing entries for two filing_urls used in mentions.
    lda_filing_url_a = "https://lda.senate.gov/api/v1/filings/uuid-0/"
    lda_filing_url_b = "https://lda.senate.gov/api/v1/filings/uuid-1/"
    (site_json / "citations.json").write_text(json.dumps({
        "traj26fact": {"kind": "derived"}, "traj25fact": {"kind": "derived"},
        "traj26fact2": {"kind": "derived"}, "hhifact": {"kind": "derived"},
        "dollarsfact": {"kind": "derived"}, "blfact": {"kind": "workbook"},
        "feedfact": {"kind": "derived"},
        "detfact0": {"kind": "jbook_pdf"},
        "detfact1": {"kind": "jbook_pdf"},
        "detfact2": {"kind": "jbook_pdf"},
        "detfact3": {"kind": "jbook_pdf"},
        "detfact4": {"kind": "jbook_pdf"},
        # lda_filing entries — citable fact_ids for lobbying mentions
        "ldafact_a": {"kind": "lda_filing", "official_url": lda_filing_url_a},
        "ldafact_b": {"kind": "lda_filing", "official_url": lda_filing_url_b},
    }))

    (snapshots / "index.json").write_text(json.dumps({"snapshots": [
        {"sha256": SHA, "url": SNAP_URL, "retrieved_at": "2026-06-12T00:00:00Z",
         "title": "Article", "pe_bli": PE, "matched_term": "sciences"},
    ]}))
    (snapshots / f"{SHA}.json").write_text(json.dumps({
        "url": SNAP_URL, "retrieved_at": "2026-06-12T00:00:00Z", "sha256": SHA,
        "title": "Article", "text": "S" * 40_000,
    }))

    categories = tmp_path / "program_categories.csv"
    categories.write_text(
        "pe_bli,category,rationale,source_ref\n"
        f"{PE},default,broad portfolio,ProgramElement[5]\n"
        f"{PE2},hypersonics,hypersonic tech,snapshot:{SHA}\n"
    )

    return SimpleNamespace(
        site_json=site_json, snapshots=snapshots, categories=categories,
        tmp=tmp_path,
        lda_url_a=lda_filing_url_a,
        lda_url_b=lda_filing_url_b,
    )


@pytest.fixture()
def fixture_duckdb(tmp_path):
    db = tmp_path / "fixture.duckdb"
    con = duckdb.connect(str(db))
    # account/account_title: the member identity the exporter resolves a
    # program page with. A dim_programs PRESENT without them is a stale mart
    # and stops the export (Task 27 fix round 2, 2026-09-19), so the fixture
    # declares them — NULL, which is what a code naming ONE program carries.
    con.execute("create table dim_programs (pe_bli varchar, org varchar,"
                " exhibit_family varchar, project_count bigint,"
                " fy2024_actual_millions double, fully_reconciled boolean,"
                " title varchar, account varchar, account_title varchar)")
    con.execute("create table fct_budget_trajectory (pe_bli varchar,"
                " organization varchar, fy2024_actuals double,"
                " fy2025_total double, fy2026_total double,"
                " fy2526_change double, fy2526_pct_change double)")
    rows = [
        (PE, "DARPA", "Defense Research Sciences", "DARPA", 100.0),
        (PE2, "OSD", "Joint Hypersonic Technology", "OSD", 500.0),
    ]
    for pe, org, title, wb, total in rows:
        con.execute("insert into dim_programs values (?,?,?,?,?,?,?,?,?)",
                    [pe, org, "rdte", 1, 1.0, True, title, None, None])
        con.execute("insert into fct_budget_trajectory values (?,?,?,?,?,?,?)",
                    [pe, wb, 1.0, 1.0, total, 0.0, 0.0])
    con.close()
    return db


# ---------------------------------------------------------------------------
# Fake Anthropic client (no network)
# ---------------------------------------------------------------------------


def _heuristic_count_call(kw) -> int:
    text = "".join(m["content"] for m in kw.get("messages", []))
    system = kw.get("system") or ""
    if isinstance(system, list):
        system = "".join(b.get("text", "") for b in system)
    return heuristic_token_count(system + text) if system else heuristic_token_count(text)


class FakeBatches:
    def __init__(self, results_items=None, statuses=("ended",)):
        self.created: list = []
        self._results = list(results_items or [])
        self._statuses = list(statuses)

    def create(self, requests):
        self.created.append(requests)
        return SimpleNamespace(id="msgbatch_test123",
                               processing_status="in_progress")

    def retrieve(self, batch_id):
        status = (self._statuses.pop(0) if len(self._statuses) > 1
                  else self._statuses[0])
        return SimpleNamespace(id=batch_id, processing_status=status)

    def results(self, batch_id):
        return iter(self._results)


class FakeMessages:
    def __init__(self, batches, fixed_input_tokens=None):
        self.batches = batches
        self.fixed = fixed_input_tokens
        self.count_calls: list = []

    def count_tokens(self, **kw):
        self.count_calls.append(kw)
        n = self.fixed if self.fixed is not None else _heuristic_count_call(kw)
        return SimpleNamespace(input_tokens=n)


class FakeClient:
    def __init__(self, results_items=None, statuses=("ended",),
                 fixed_input_tokens=None):
        self.batches = FakeBatches(results_items, statuses)
        self.messages = FakeMessages(self.batches, fixed_input_tokens)


def _valid_dossier(url_claims: int = 1, fact_claims: int = 4) -> dict:
    """Schema-valid dossier with controllable warehouse/url claim mix."""
    facts = ["traj26fact", "hhifact", "blfact", "feedfact", "detfact0",
             "traj25fact", "dollarsfact", "traj26fact2"]
    fact_iter = iter(facts * 10)

    def fact_claim():
        return {"text": "A warehouse-cited claim.",
                "citation": {"fact_id": next(fact_iter)}}

    recent = [{"text": "News claim.", "citation": {"url": SNAP_URL}}
              for _ in range(url_claims)]
    n_each = max(1, fact_claims // 3)
    return {
        "what_it_is": {"claims": [fact_claim() for _ in range(n_each)]},
        "why_it_matters": {"claims": [fact_claim() for _ in range(n_each)]},
        "players": {"claims": [fact_claim()
                               for _ in range(fact_claims - 2 * n_each)]},
        "recent_developments": {"claims": recent},
    }


def _succeeded(pe_bli: str, dossier: dict) -> SimpleNamespace:
    return SimpleNamespace(
        custom_id=f"dossier-{pe_bli}",
        result=SimpleNamespace(
            type="succeeded",
            message=SimpleNamespace(
                content=[SimpleNamespace(type="text",
                                         text=json.dumps(dossier))],
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=10, output_tokens=20),
            ),
        ),
    )


def _errored(pe_bli: str) -> SimpleNamespace:
    return SimpleNamespace(
        custom_id=f"dossier-{pe_bli}",
        result=SimpleNamespace(
            type="errored",
            error=SimpleNamespace(type="invalid_request", message="boom"),
        ),
    )


# ---------------------------------------------------------------------------
# Schema shape
# ---------------------------------------------------------------------------


class TestSchema:
    def test_sections_and_required(self):
        assert set(DOSSIER_SCHEMA["properties"]) == set(ALL_SECTIONS)
        assert set(DOSSIER_SCHEMA["required"]) == set(ALL_SECTIONS)
        assert set(REQUIRED_SECTIONS) == {"what_it_is", "why_it_matters",
                                          "players"}
        assert DOSSIER_SCHEMA["additionalProperties"] is False

    def test_claim_and_citation_shape(self):
        section = DOSSIER_SCHEMA["properties"]["what_it_is"]
        assert section["required"] == ["claims"]
        assert section["additionalProperties"] is False
        claim = section["properties"]["claims"]["items"]
        assert set(claim["required"]) == {"text", "citation"}
        assert claim["additionalProperties"] is False
        branches = claim["properties"]["citation"]["anyOf"]
        keys = {tuple(b["required"]) for b in branches}
        assert keys == {("fact_id",), ("url",)}
        assert all(b["additionalProperties"] is False for b in branches)


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


class TestTokenCounting:
    def test_heuristic_is_chars_over_four(self):
        assert heuristic_token_count("abcd" * 3) == 3
        assert heuristic_token_count("abcde") == 2
        assert heuristic_token_count("") == 1

    def test_counter_prefers_count_tokens_when_client_present(self):
        client = FakeClient(fixed_input_tokens=777)
        counter = make_token_counter(client)
        assert counter("anything") == 777
        assert client.messages.count_calls[0]["model"] == MODEL

    def test_counter_falls_back_to_heuristic(self):
        assert make_token_counter(None) is heuristic_token_count


# ---------------------------------------------------------------------------
# Bundle building + trimming
# ---------------------------------------------------------------------------


def _bundle_json(b: dict) -> dict:
    text = b["text"]
    return json.loads(text[text.index("{"):])


class TestBuildBundle:
    def _build(self, fx, **kw):
        return build_bundle(PE, site_json_dir=fx.site_json,
                            snapshots_dir=fx.snapshots,
                            categories_csv=fx.categories, **kw)

    def test_contents(self, site_fixture):
        b = self._build(site_fixture)
        data = _bundle_json(b)
        assert data["pe_bli"] == PE
        # narratives FULL
        assert data["narratives"][0]["body"] == "M" * 3000
        # top-25 caps
        assert len(data["mentions"]) == 25
        assert len(data["awards"]) == 25
        assert len(data["projects"]) == 25
        # trajectory + its fact_ids
        assert data["program"]["trajectory"]["fy2026_total"] == 100.0
        assert data["program"]["trajectory_fact_ids"]["fy2026_total"] == "traj26fact"
        # feed events scoped to this pe_bli
        assert [e["figure_fact_id"] for e in data["feed_events"]] == ["feedfact"]
        # flows summary
        assert data["flows"]["award_count"] == 12
        assert len(data["flows"]["top_awards"]) == 10
        assert data["flows"]["total_dollars"] == pytest.approx(1200.0)
        # category row
        assert data["category"]["category"] == "default"
        # snapshots: title+url+text (capped at the pre-trim cap)
        assert data["snapshots"][0]["url"] == SNAP_URL
        assert data["snapshots"][0]["title"] == "Article"
        assert len(data["snapshots"][0]["text"]) == 8000

    def test_concentration_block_is_the_published_basis_only(self, site_fixture):
        """ROADMAP #80 fix round 1, finding 12: the prompt must not be able to
        cite a basis the page does not publish. The all-links fids are in
        programs.json (they feed /methodology/ and the download) and must not
        appear anywhere in the rendered bundle."""
        rendered = self._build(site_fixture)
        data = _bundle_json(rendered)
        assert data["program"]["hhi"] == {
            "basis": "high-confidence award links only",
            "hhi": 3900.0, "hhi_fact_id": "hhifact",
            "program_dollars": 3e8, "program_dollars_fact_id": "dollarsfact",
            "top_family": "BOEING", "family_count": 4, "award_count": 9,
        }
        assert "allhhifact" not in rendered
        assert "alldollarsfact" not in rendered

    def test_flows_absent_when_no_sidecar(self, site_fixture):
        b = build_bundle(PE2, site_json_dir=site_fixture.site_json,
                         snapshots_dir=site_fixture.snapshots,
                         categories_csv=site_fixture.categories)
        data = _bundle_json(b)
        assert data["flows"] is None
        assert data["snapshots"] == []  # no matched snapshots for PE2

    def test_no_trim_under_default_cap(self, site_fixture):
        b = self._build(site_fixture)
        assert b["tokens"] <= BUNDLE_TOKEN_CAP
        assert b["trim_stages"] == []

    def test_trimming_respects_cap_and_stage_order(self, site_fixture):
        b = self._build(site_fixture, token_cap=3000)
        assert b["tokens"] <= 3000
        assert b["trim_stages"]  # something was trimmed
        stage_names = [name for name, _fn in _TRIM_STAGES]
        applied = [s for s in b["trim_stages"] if s != "hard_truncated"]
        # stages apply strictly in order (a prefix of the stage list)
        assert applied == stage_names[: len(applied)]
        # snapshots give way before narratives are touched
        if "narratives_2000" in applied:
            assert "snapshots_top3" in applied

    def test_hard_truncation_guarantee(self, site_fixture):
        b = self._build(site_fixture, token_cap=100)
        assert b["trim_stages"][-1] == "hard_truncated"
        assert b["tokens"] <= 100

    def test_count_tokens_used_for_trimming_when_client_given(self, site_fixture):
        client = FakeClient()
        counter = make_token_counter(client)
        self._build(site_fixture, token_counter=counter)
        assert client.messages.count_calls  # API counting, not heuristic


# ---------------------------------------------------------------------------
# Bundle hygiene — fact_id filtering, xml_path stripping, mention annotation
# ---------------------------------------------------------------------------


class TestBundleHygiene:
    """Tests that build_bundle applies citation hygiene at assemble time."""

    def _build_with_keyset(self, fx, **kw):
        """Build with citations_keyset loaded from the fixture's citations.json."""
        keyset = _load_citations_keyset(fx.site_json)
        lda_map = _lda_url_to_fact_id(fx.site_json)
        return build_bundle(
            PE,
            site_json_dir=fx.site_json,
            snapshots_dir=fx.snapshots,
            categories_csv=fx.categories,
            citations_keyset=keyset,
            lda_url_map=lda_map,
            **kw,
        )

    def test_absent_fact_id_projects_filtered_and_counted(
        self, site_fixture, capsys
    ):
        """Project rows whose fact_id is absent from citations.json must be dropped."""
        # Fixture has detfact0..4 in citations.json, detfact5..29 absent.
        # The 30 projects are sorted by amount_millions descending: indices 29→0.
        # So detfact5..29 (indices 5-29) are the highest-amount projects and
        # will come first, all absent → filtered. detfact0..4 will pass.
        b = self._build_with_keyset(site_fixture)
        data = _bundle_json(b)

        present_fids = {p["fact_id"] for p in data["projects"]}
        keyset = _load_citations_keyset(site_fixture.site_json)
        assert all(fid in keyset for fid in present_fids), (
            f"Projects contain fact_ids absent from citations.json: "
            f"{present_fids - keyset}"
        )
        # At most 5 projects survive (detfact0..4), all valid
        assert len(data["projects"]) <= 5

        # Loud print when rows were dropped
        captured = capsys.readouterr().out
        assert "FILTERED" in captured

    def test_no_keyset_does_not_filter(self, site_fixture):
        """Without citations_keyset, projects are NOT filtered (backward compat)."""
        b = build_bundle(
            PE,
            site_json_dir=site_fixture.site_json,
            snapshots_dir=site_fixture.snapshots,
            categories_csv=site_fixture.categories,
        )
        data = _bundle_json(b)
        # Without filtering, all 25 top projects are included (cap=TOP_N_LIST=25)
        assert len(data["projects"]) == 25

    def test_xml_path_stripped_from_narratives(self, site_fixture):
        """xml_path must be removed from narrative rows — it is not citable."""
        b = self._build_with_keyset(site_fixture)
        data = _bundle_json(b)
        for narr in data["narratives"]:
            assert "xml_path" not in narr, (
                f"xml_path must be stripped from narratives; found in {narr}"
            )
        # Narrative body and other fields survive intact
        assert data["narratives"][0]["body"] == "M" * 3000
        assert data["narratives"][0]["kind"] == "mission"

    def test_mention_carries_citable_fact_id(self, site_fixture):
        """Mentions with a known filing_url must get a citable_fact_id annotation."""
        b = self._build_with_keyset(site_fixture)
        data = _bundle_json(b)
        # uuid-0 and uuid-1 map to ldafact_a / ldafact_b in the fixture
        m0 = next(m for m in data["mentions"] if "uuid-0" in m.get("filing_url", "")
                  or "uuid-0" in m.get("filing_uuid", ""))
        assert "citable_fact_id" in m0, (
            "Mention with known filing_url must carry citable_fact_id"
        )
        assert m0["citable_fact_id"] == "ldafact_a"

    def test_mention_filing_url_labeled_not_citable(self, site_fixture):
        """filing_url on each mention must be labeled '(reference link, NOT a citable url)'."""
        b = self._build_with_keyset(site_fixture)
        data = _bundle_json(b)
        for m in data["mentions"]:
            raw_url = m.get("filing_url", "")
            if raw_url:
                assert "(reference link, NOT a citable url)" in raw_url, (
                    f"filing_url must carry the NOT-citable label; got: {raw_url!r}"
                )

    def test_mention_without_known_url_has_no_citable_fact_id(self, site_fixture):
        """Mentions whose filing_url has no match in lda_url_map get no citable_fact_id."""
        b = self._build_with_keyset(site_fixture)
        data = _bundle_json(b)
        # filing_url "uuid-2" and beyond have no lda entry in fixture citations.json
        unknown = [m for m in data["mentions"]
                   if "uuid-2" in m.get("filing_url", "")]
        assert unknown, "Expected at least one mention with an unknown filing_url"
        for m in unknown:
            assert "citable_fact_id" not in m

    def test_preamble_contains_negative_rules(self):
        """SHARED_PREAMBLE must contain the three explicit negative rules."""
        assert "XML anchors" in SHARED_PREAMBLE
        assert "ProgramElement" in SHARED_PREAMBLE
        assert "lda.senate.gov" in SHARED_PREAMBLE
        assert "NOT a citable url" in SHARED_PREAMBLE
        assert "NEWS SNAPSHOTS" in SHARED_PREAMBLE


# ---------------------------------------------------------------------------
# Estimator math
# ---------------------------------------------------------------------------


class TestEstimator:
    def test_rates(self):
        assert BATCH_INPUT_USD_PER_MTOK == 2.50
        assert BATCH_OUTPUT_USD_PER_MTOK == 12.50
        assert MAX_OUTPUT_TOKENS == 16000

    def test_fixed_token_math(self, monkeypatch):
        """Input math, with the output predictor pinned so this test measures
        one thing. The output basis has its own two tests below."""
        monkeypatch.setattr(batch, "_observed_mean_output_tokens", lambda: None)
        client = FakeClient(fixed_input_tokens=10_000)
        bundles = [{"pe_bli": "A", "title": "", "text": "x"},
                   {"pe_bli": "B", "title": "", "text": "y"}]
        est = estimate_cost(bundles, client=client)
        p = est["per_dossier"][0]
        assert p["input_tokens"] == 10_000
        assert p["input_usd"] == pytest.approx(0.025)     # 10k * $2.50/MTok
        assert p["output_usd"] == pytest.approx(0.20)     # 16k * $12.50/MTok
        assert p["total_usd"] == pytest.approx(0.225)
        assert est["total_usd"] == pytest.approx(0.45)
        assert est["output_basis"] == "cap"

    def test_output_predicted_from_archived_runs_when_available(self, monkeypatch):
        """The cap is a CEILING, not a forecast.

        Assuming every dossier emits MAX_OUTPUT_TOKENS ran the estimate ~6x
        high and is why 15 needed dossiers sat undone: quoted $3.31, actual
        $0.55. When archived runs exist, predict from them.
        """
        monkeypatch.setattr(batch, "_observed_mean_output_tokens", lambda: 1_600)
        client = FakeClient(fixed_input_tokens=10_000)
        est = estimate_cost([{"pe_bli": "A", "title": "", "text": "x"}],
                            client=client)
        p = est["per_dossier"][0]
        assert p["output_tokens"] == 1_600
        assert p["output_usd"] == pytest.approx(0.02)     # 1.6k * $12.50/MTok
        assert est["output_basis"] == "observed"
        assert est["output_tokens_assumed"] == 1_600

    def test_predictor_refuses_on_too_few_samples(self, tmp_path, monkeypatch):
        """Fewer than 5 archived runs is not a distribution — fall back to the
        cap rather than predict from noise."""
        assert batch._observed_mean_output_tokens() is not None  # real archive
        monkeypatch.setattr(
            batch.Path, "resolve", lambda self: tmp_path / "nope" / "x" / "y" / "z"
        )
        # a directory with no runs at all must not produce a prediction
        assert batch._observed_mean_output_tokens() is None

    def test_heuristic_path_counts_system_plus_bundle(self):
        text = "a" * 4000  # 1,000 tokens heuristic
        est = estimate_cost([{"pe_bli": "A", "title": "", "text": text}])
        expected = 1000 + math.ceil(len(SHARED_PREAMBLE) / 4)
        assert est["per_dossier"][0]["input_tokens"] == expected

    def test_count_tokens_receives_system_preamble(self):
        client = FakeClient(fixed_input_tokens=5)
        estimate_cost([{"pe_bli": "A", "title": "", "text": "x"}], client=client)
        call = client.messages.count_calls[0]
        assert call["system"] == SHARED_PREAMBLE
        assert call["model"] == MODEL


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


class TestSubmit:
    def _submit(self, fx, db, client, **kw):
        return submit(
            duckdb_path=db, site_json_dir=fx.site_json,
            snapshots_dir=fx.snapshots, categories_csv=fx.categories,
            raw_dir=fx.tmp / "dossiers-raw", client=client, **kw,
        )

    def test_blocked_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit) as exc:
            require_client(None)
        msg = str(exc.value)
        assert "ANTHROPIC_API_KEY" in msg
        assert "export ANTHROPIC_API_KEY" in msg

    def test_submit_blocked_without_api_key(self, site_fixture, fixture_duckdb,
                                             monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit) as exc:
            self._submit(site_fixture, fixture_duckdb, None)
        assert "ANTHROPIC_API_KEY" in str(exc.value)

    def test_happy_path_creates_batch_and_meta(self, site_fixture,
                                               fixture_duckdb, capsys):
        client = FakeClient()
        summary = self._submit(site_fixture, fixture_duckdb, client)
        assert summary["batch_id"] == "msgbatch_test123"
        assert summary["requests"] == 2

        # requests per recon §G
        (requests,) = client.batches.created
        ids = sorted(r["custom_id"] for r in requests)
        assert ids == [f"dossier-{PE}", f"dossier-{PE2}"]
        params = requests[0]["params"]
        assert params["model"] == MODEL
        assert params["max_tokens"] == MAX_OUTPUT_TOKENS
        assert params["output_config"]["format"]["schema"] == DOSSIER_SCHEMA
        sys_block = params["system"][0]
        assert sys_block["text"] == SHARED_PREAMBLE
        assert sys_block["cache_control"] == {"type": "ephemeral", "ttl": "1h"}

        # batch_meta.json persisted to the committed raw dir
        meta = json.loads(
            (site_fixture.tmp / "dossiers-raw" / "batch_meta.json").read_text())
        assert meta["batch_id"] == "msgbatch_test123"
        assert meta["request_count"] == 2
        assert set(meta["pe_blis"]) == {PE, PE2}
        assert meta["estimated_usd"] == pytest.approx(summary["estimated_usd"],
                                                      abs=1e-3)

        # per-dossier estimate + total printed
        out = capsys.readouterr().out
        assert PE in out and PE2 in out
        assert "TOTAL estimated $" in out

    def test_cost_cap_abort_creates_no_batch(self, site_fixture,
                                             fixture_duckdb):
        client = FakeClient(fixed_input_tokens=30_000_000)  # ~$75/dossier
        with pytest.raises(SystemExit) as exc:
            self._submit(site_fixture, fixture_duckdb, client)
        assert "exceeds" in str(exc.value)
        assert "no batch created" in str(exc.value).lower()
        assert client.batches.created == []
        assert not (site_fixture.tmp / "dossiers-raw" / "batch_meta.json").exists()

    def test_cost_cap_is_adjustable(self, site_fixture, fixture_duckdb):
        client = FakeClient(fixed_input_tokens=30_000_000)
        summary = self._submit(site_fixture, fixture_duckdb, client,
                               cost_cap=1000.0)
        assert summary["requests"] == 2


# ---------------------------------------------------------------------------
# Collect
# ---------------------------------------------------------------------------


class TestCollect:
    def _meta(self, raw_dir: Path):
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "batch_meta.json").write_text(json.dumps(
            {"batch_id": "msgbatch_test123", "model": MODEL,
             "request_count": 2, "pe_blis": [PE, PE2]}))

    def test_requires_meta(self, tmp_path):
        client = FakeClient()
        with pytest.raises(SystemExit) as exc:
            collect(raw_dir=tmp_path / "raw", out_dir=tmp_path / "out",
                    client=client)
        assert "submit" in str(exc.value)

    def test_polls_until_ended_then_writes(self, tmp_path, capsys):
        raw, out = tmp_path / "raw", tmp_path / "out"
        self._meta(raw)
        dossier = _valid_dossier()
        client = FakeClient(
            results_items=[_succeeded(PE, dossier), _errored(PE2)],
            statuses=("in_progress", "in_progress", "ended"),
        )
        sleeps: list[float] = []
        summary = collect(raw_dir=raw, out_dir=out, client=client,
                          poll_interval=1.0, sleep=sleeps.append)
        assert sleeps == [1.0, 1.0]

        # raw archive (paid artifact) for the succeeded item
        raw_doc = json.loads((raw / f"{PE}.json").read_text())
        assert raw_doc["custom_id"] == f"dossier-{PE}"
        assert raw_doc["message"]["content"][0]["type"] == "text"

        # parsed dossier written
        parsed = json.loads((out / f"{PE}.json").read_text())
        assert parsed["pe_bli"] == PE
        assert parsed["dossier"] == dossier

        # errored item: loud listing + summary
        assert summary["ok"] is False
        assert summary["succeeded"] == [PE]
        assert summary["failed"][0]["pe_bli"] == PE2
        assert summary["failed"][0]["reason"] == "errored"
        captured = capsys.readouterr().out
        assert f"FAILED {PE2}" in captured
        assert not (out / f"{PE2}.json").exists()

    def test_schema_invalid_result_is_failure_but_raw_archived(self, tmp_path,
                                                               capsys):
        raw, out = tmp_path / "raw", tmp_path / "out"
        self._meta(raw)
        bad = _valid_dossier()
        bad["extra_section"] = {"claims": []}
        client = FakeClient(results_items=[_succeeded(PE, bad)])
        summary = collect(raw_dir=raw, out_dir=out, client=client)
        assert summary["ok"] is False
        assert "schema" in summary["failed"][0]["reason"]
        assert (raw / f"{PE}.json").exists()       # paid artifact kept
        assert not (out / f"{PE}.json").exists()   # but never published
        assert "FAILED" in capsys.readouterr().out

    def test_non_json_text_is_failure(self, tmp_path):
        raw, out = tmp_path / "raw", tmp_path / "out"
        self._meta(raw)
        item = _succeeded(PE, {})
        item.result.message.content[0].text = "not json {"
        client = FakeClient(results_items=[item])
        summary = collect(raw_dir=raw, out_dir=out, client=client)
        assert summary["ok"] is False
        assert "invalid JSON" in summary["failed"][0]["reason"]

    def test_blocked_without_api_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit) as exc:
            collect(raw_dir=tmp_path, out_dir=tmp_path)
        assert "ANTHROPIC_API_KEY" in str(exc.value)

    # --- Citation membership checks at collect time ---

    def _cit_refs(self, tmp_path: Path, *, snap_url: str | None):
        """Write citations.json + snapshots/index.json; return paths."""
        citations_path = tmp_path / "citations.json"
        citations_path.write_text(json.dumps({"traj26fact": {}, "hhifact": {},
                                               "blfact": {}, "feedfact": {},
                                               "detfact0": {}, "traj25fact": {},
                                               "dollarsfact": {}, "traj26fact2": {}}))
        snap_dir = tmp_path / "snapshots"
        snap_dir.mkdir(exist_ok=True)
        snaps = []
        if snap_url:
            snaps.append({"sha256": SHA, "url": snap_url,
                          "retrieved_at": "2026-06-01T00:00:00Z",
                          "title": "T", "pe_bli": PE, "matched_term": "t"})
        (snap_dir / "index.json").write_text(json.dumps({"snapshots": snaps}))
        return citations_path, snap_dir / "index.json"

    def test_collect_rejects_anchor_url_when_refs_present(self, tmp_path, capsys):
        """PROOF-IT-CAN-FAIL: anchor-as-url rejected at collect time when refs exist."""
        raw, out = tmp_path / "raw", tmp_path / "out"
        self._meta(raw)
        citations_path, snapshots_index = self._cit_refs(tmp_path, snap_url=None)

        # Dossier with anchor url citation
        bad = _valid_dossier(url_claims=0)
        bad["recent_developments"]["claims"] = [
            {"text": "Broken.", "citation": {"url": "ProgramElement[0]"}}
        ]
        client = FakeClient(results_items=[_succeeded(PE, bad)])
        summary = collect(raw_dir=raw, out_dir=out, client=client,
                          citations_path=citations_path,
                          snapshots_index=snapshots_index)

        assert summary["ok"] is False
        assert summary["failed"][0]["pe_bli"] == PE
        assert "citations:" in summary["failed"][0]["reason"]
        assert "ProgramElement[0]" in summary["failed"][0]["reason"]
        assert not (out / f"{PE}.json").exists()
        out_text = capsys.readouterr().out
        assert "REJECTED" in out_text

    def test_collect_accepts_valid_refs_when_refs_present(self, tmp_path):
        """When all citations resolve, dossier is written normally."""
        raw, out = tmp_path / "raw", tmp_path / "out"
        self._meta(raw)
        citations_path, snapshots_index = self._cit_refs(tmp_path, snap_url=SNAP_URL)

        good = _valid_dossier(url_claims=1)  # uses SNAP_URL
        client = FakeClient(results_items=[_succeeded(PE, good)])
        summary = collect(raw_dir=raw, out_dir=out, client=client,
                          citations_path=citations_path,
                          snapshots_index=snapshots_index)

        assert summary["ok"] is True
        assert summary["succeeded"] == [PE]
        assert (out / f"{PE}.json").exists()

    def test_collect_shape_only_when_refs_absent(self, tmp_path):
        """When reference files are absent, shape-only validation (no membership)."""
        raw, out = tmp_path / "raw", tmp_path / "out"
        self._meta(raw)
        # No citations_path / snapshots_index provided
        bad = _valid_dossier(url_claims=0)
        bad["recent_developments"]["claims"] = [
            {"text": "Anchor.", "citation": {"url": "ProgramElement[0]"}}
        ]
        client = FakeClient(results_items=[_succeeded(PE, bad)])
        # Without reference files, anchor url passes (shape is valid)
        summary = collect(raw_dir=raw, out_dir=out, client=client)
        assert summary["ok"] is True
        assert summary["succeeded"] == [PE]


# ---------------------------------------------------------------------------
# validate_dossier
# ---------------------------------------------------------------------------


class TestValidateDossier:
    def test_valid(self):
        assert validate_dossier(_valid_dossier()) == []

    def test_empty_recent_developments_is_valid(self):
        assert validate_dossier(_valid_dossier(url_claims=0)) == []

    def test_missing_section(self):
        d = _valid_dossier()
        del d["players"]
        assert any("missing section: players" in e for e in validate_dossier(d))

    def test_extra_top_level_key(self):
        d = _valid_dossier()
        d["bonus"] = {"claims": []}
        assert any("unexpected top-level" in e for e in validate_dossier(d))

    def test_claim_without_citation(self):
        d = _valid_dossier()
        d["players"]["claims"][0] = {"text": "no cite"}
        assert any("keys must be exactly" in e for e in validate_dossier(d))

    def test_citation_with_both_keys(self):
        d = _valid_dossier()
        d["players"]["claims"][0]["citation"] = {"fact_id": "x", "url": "y"}
        assert any("citation must be" in e for e in validate_dossier(d))

    def test_citation_with_unknown_key(self):
        d = _valid_dossier()
        d["players"]["claims"][0]["citation"] = {"source": "x"}
        assert any("citation must be" in e for e in validate_dossier(d))

    def test_empty_text(self):
        d = _valid_dossier()
        d["players"]["claims"][0]["text"] = "  "
        assert any("non-empty string" in e for e in validate_dossier(d))


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


@pytest.fixture()
def split_key_duckdb(tmp_path):
    """Production's 3050 shape: a shared BLI code (PE2) whose two dim_programs
    rows differ by ACCOUNT, with every crosswalk link filed under ONE member
    (OPN) and a bare-keyed concentration figure describing exactly those
    links. PE is an ordinary single-member program with nothing at all.

    Only the columns the gate's evidence query reads are defined — the real
    marts are far wider; a narrower fixture would pass for the wrong reason
    if a future query started reading a column this one lacks (it would raise,
    and an unknown answer is never granted).
    """
    db = tmp_path / "split.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table dim_programs (pe_bli varchar, account varchar,"
                " account_title varchar, org varchar, exhibit_family varchar)")
    con.execute("insert into dim_programs values (?,?,?,?,?)",
                [PE, None, None, "DARPA", "rdte"])
    con.execute("insert into dim_programs values (?,?,?,?,?)",
                [PE2, "1611N", "Shipbuilding and Conversion, Navy", "N", "procurement"])
    con.execute("insert into dim_programs values (?,?,?,?,?)",
                [PE2, "1810N", "Other Procurement, Navy", "N", "procurement"])
    con.execute("create table fct_budget_to_awards (pe_bli varchar,"
                " account varchar, organization varchar, award_piid varchar,"
                " recipient_name varchar, recipient_uei varchar)")
    for piid in ("N0001", "N0002"):
        con.execute("insert into fct_budget_to_awards values (?,?,?,?,?,?)",
                    [PE2, "1810N", "N", piid, "HUNTINGTON INGALLS INCORPORATED",
                     "UEI-HII"])
    con.execute("create table fct_program_lobbying (pe_bli varchar,"
                " family_key varchar, evidence_kind varchar)")
    # R-DEC-DOSSIERDRIFT (round 2) fails closed on a supplied mart it cannot
    # read, so the fixture carries every column its two indexes read: the
    # concentration mart's families and dim_entities (the family leg), and
    # fct_budget_to_awards' recipients with entity_xwalk (the recipient leg).
    con.execute("create table fct_program_concentration (pe_bli varchar,"
                " hhi_all double, top_family_all varchar, hhi_high double,"
                " top_family_high varchar)")
    con.execute("insert into fct_program_concentration values (?,?,?,?,?)",
                [PE2, 4373.59, "HUNTINGTON INGALLS INDUSTRIES", None, None])
    con.execute("create table dim_entities (family_key varchar, display_name varchar)")
    con.execute("create table entity_xwalk (recipient_uei varchar,"
                " recipient_name varchar, parent_name varchar, family_key varchar)")
    con.execute("insert into entity_xwalk values (?,?,?,?)",
                ["UEI-HII", "HUNTINGTON INGALLS INCORPORATED",
                 "HUNTINGTON INGALLS INDUSTRIES INC", "HUNTINGTON INGALLS INDUSTRIES"])
    con.close()
    return db


@pytest.fixture()
def gate_fixture(site_fixture):
    """Dossier files + the surrounding reference data for gate runs."""
    dossier_dir = site_fixture.tmp / "dossiers"
    dossier_dir.mkdir()
    for pe, url_claims in ((PE, 1), (PE2, 0)):
        (dossier_dir / f"{pe}.json").write_text(json.dumps({
            "pe_bli": pe, "model": MODEL,
            "collected_at": "2026-06-12T00:00:00Z",
            "dossier": _valid_dossier(url_claims=url_claims),
        }))
    return SimpleNamespace(
        dossier_dir=dossier_dir,
        citations=site_fixture.site_json / "citations.json",
        snapshots_index=site_fixture.snapshots / "index.json",
        categories=site_fixture.categories,
        top50=[(PE, "Defense Research Sciences", "DARPA", 100.0),
               (PE2, "Joint Hypersonic Technology", "OSD", 500.0)],
        dim_pe={PE, PE2},
    )


def _run_gate(fx, **kw):
    return dossier_gate(fx.dossier_dir, fx.citations, fx.snapshots_index,
                        fx.categories, fx.top50,
                        dim_programs_pe=fx.dim_pe, **kw)


class TestGate:
    def test_pass(self, gate_fixture):
        res = _run_gate(gate_fixture)
        assert res["ok"], res
        assert res["checks"]["warehouse_ratio"]["ratio"] >= 0.80
        assert res["totals"]["dossiers"] == 2

    def test_recent_developments_may_be_empty(self, gate_fixture):
        # PE2's dossier already has zero recent_developments claims
        res = _run_gate(gate_fixture)
        assert res["checks"]["required_sections"]["ok"]
        assert res["ok"]

    def test_unresolvable_fact_id_fails(self, gate_fixture):
        path = gate_fixture.dossier_dir / f"{PE}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"][0]["citation"] = {
            "fact_id": "not-a-real-fact"}
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture)
        assert not res["ok"]
        bad = res["checks"]["citations_resolvable"]
        assert not bad["ok"]
        assert bad["unresolved"][0]["fact_id"] == "not-a-real-fact"

    def test_unresolvable_url_fails(self, gate_fixture):
        path = gate_fixture.dossier_dir / f"{PE}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["recent_developments"]["claims"][0]["citation"] = {
            "url": "https://not-a-snapshot.example.com/"}
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture)
        assert not res["checks"]["citations_resolvable"]["ok"]

    def test_warehouse_ratio_below_floor_fails(self, gate_fixture):
        # rewrite PE's dossier so url claims dominate: 3 fact + 9 url = 25%+...
        path = gate_fixture.dossier_dir / f"{PE}.json"
        doc = json.loads(path.read_text())
        doc["dossier"] = _valid_dossier(url_claims=9, fact_claims=3)
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture)
        ratio_check = res["checks"]["warehouse_ratio"]
        # corpus-wide: PE has 3 fact + 9 url, PE2 has 4 fact -> 7/16 < 0.8
        assert ratio_check["ratio"] == pytest.approx(7 / 16)
        assert not ratio_check["ok"]
        assert not res["ok"]

    def test_empty_required_section_fails(self, gate_fixture):
        path = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture)
        assert not res["checks"]["required_sections"]["ok"]
        assert f"{PE2}: players" in res["checks"]["required_sections"]["empty"]

    # -----------------------------------------------------------------------
    # required_sections TIGHTENING (follow-up to #52, 2026-08): an empty
    # required section still fails UNLESS the sidecar records the section's
    # own drop count AND the built page actually discloses it. Three arms,
    # matching the PR description's own "prove it can still fail" ask:
    #   1. drop recorded, but no built site available to verify   -> FAIL
    #   2. drop recorded, built site exists but does NOT disclose -> FAIL
    #   3. drop recorded AND the built page discloses it          -> PASS
    # Arm 1's sibling (no drop recorded at all) is
    # test_empty_required_section_fails above — unchanged by this feature.
    # -----------------------------------------------------------------------

    def test_arm1_drop_recorded_but_no_built_site_still_fails(self, gate_fixture):
        """No built_site_dir passed (the standalone `dossiers gate` shape,
        run right after collect, before any site build exists) — the
        exception cannot be granted without something to verify against, so
        this must fail exactly as the ORIGINAL, unconditional rule always
        did. Recording a drop is necessary but not sufficient."""
        path = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        doc["dropped_claims"] = 3
        doc["dropped_claims_by_section"] = {"players": 3}
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture)  # no built_site_dir kwarg
        assert not res["checks"]["required_sections"]["ok"]
        assert f"{PE2}: players" in res["checks"]["required_sections"]["empty"]

    def test_arm2_drop_recorded_but_page_does_not_disclose_it_still_fails(
        self, gate_fixture, site_fixture,
    ):
        """A built site IS available, but the actual page — a renderer
        regression, or simply the wrong page — does not carry the
        disclosure. The gate must check the ARTIFACT, not the sidecar's own
        say-so; a claimed drop with no visible correction note is exactly
        the silent-content risk this whole feature exists to prevent."""
        path = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        doc["dropped_claims"] = 3
        doc["dropped_claims_by_section"] = {"players": 3}
        path.write_text(json.dumps(doc))
        built = site_fixture.tmp / "out"
        (built / "program" / PE2).mkdir(parents=True)
        (built / "program" / PE2 / "index.html").write_text(
            "<html><body>no correction note anywhere on this page</body></html>"
        )
        res = _run_gate(gate_fixture, built_site_dir=built)
        assert not res["checks"]["required_sections"]["ok"]
        assert f"{PE2}: players" in res["checks"]["required_sections"]["empty"]

    def test_arm2b_page_carries_the_attribute_at_zero_still_fails(
        self, gate_fixture, site_fixture,
    ):
        """A present-but-zero attribute is a sidecar/page disagreement, not
        a disclosure — must not be treated as one."""
        path = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        doc["dropped_claims"] = 3
        doc["dropped_claims_by_section"] = {"players": 3}
        path.write_text(json.dumps(doc))
        built = site_fixture.tmp / "out"
        (built / "program" / PE2).mkdir(parents=True)
        (built / "program" / PE2 / "index.html").write_text(
            '<html><body><p data-dossier-dropped-claims="0">nothing removed</p></body></html>'
        )
        res = _run_gate(gate_fixture, built_site_dir=built)
        assert not res["checks"]["required_sections"]["ok"]

    def test_arm3_drop_recorded_and_page_discloses_it_passes(
        self, gate_fixture, site_fixture,
    ):
        """The ONLY situation that may pass with an empty required section —
        strictly NARROWER than the old rule, which never permitted any.
        Both conditions genuinely hold: the sidecar attributes the empty
        section to a citation-membership drop, and the built page's own
        DOM proves a reader will see the correction note."""
        path = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        doc["dropped_claims"] = 3
        doc["dropped_claims_by_section"] = {"players": 3}
        path.write_text(json.dumps(doc))
        built = site_fixture.tmp / "out"
        (built / "program" / PE2).mkdir(parents=True)
        (built / "program" / PE2 / "index.html").write_text(
            '<html><body><p data-note-kind="scope" data-dossier-dropped-claims="3">'
            "3 claims removed: they cited sources the site could not"
            " resolve.</p></body></html>"
        )
        res = _run_gate(gate_fixture, built_site_dir=built)
        assert res["checks"]["required_sections"]["ok"], res["checks"]["required_sections"]
        assert res["ok"]

    def test_a_section_with_no_claims_and_no_drop_still_fails_even_with_a_built_site(
        self, gate_fixture, site_fixture,
    ):
        """The exception is scoped to genuinely-dropped sections only — a
        built site being available must not, by itself, excuse an empty
        section that was never populated in the first place (the ORIGINAL
        defect this check exists to catch)."""
        path = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        # No dropped_claims_by_section at all — this section is empty for
        # some other (unknown, unproven-safe) reason.
        path.write_text(json.dumps(doc))
        built = site_fixture.tmp / "out"
        (built / "program" / PE2).mkdir(parents=True)
        (built / "program" / PE2 / "index.html").write_text(
            '<html><body><p data-dossier-dropped-claims="3">disclosed</p></body></html>'
        )
        res = _run_gate(gate_fixture, built_site_dir=built)
        assert not res["checks"]["required_sections"]["ok"]

    # -----------------------------------------------------------------------
    # NO-EVIDENCE EXCEPTION, PAGE-KEYED (Sprint E's arm, re-keyed by chain-B
    # fix 2 round 2, 2026-09-12). 'players' can only cite award recipients,
    # lobbying mentions or supplier concentration. A page with NONE of those
    # to cite has no players to name — but the question has to be asked at
    # the PAGE's identity, not at the bare pe_bli: a shared BLI code's two
    # members are two pages, and the sibling's links are not this page's.
    # The fixture is production's 3050 shape — every link on the shared code
    # sits on the OPN member's account, the SCN member publishes none.
    #   1. the member with nothing to cite            -> EXEMPT, named
    #   2. its linked sibling, same warehouse         -> FAILS
    #   3. the unit test of the keying itself, both ways + the bare stub
    #   4. a bare-code lobbying row: shared code -> does not deny (R-INT-9
    #      withholds it from every member); non-shared code -> FAILS
    #      (R-DEC-DOSSIER, 2026-09-26 — the block below)
    #   5. a non-split program's own concentration row -> FAILS
    #   6. no duckdb_path supplied                    -> cannot be granted
    #   7. the exemption is players-only
    # -----------------------------------------------------------------------

    @staticmethod
    def _slug_dossier_with_empty_section(gate_fixture, slug, section="players"):
        """Re-file PE2's dossier under a member SLUG (production's
        "3010-SCN.json" shape, resolved by the gate's sibling lookup) with
        one required section emptied."""
        src = gate_fixture.dossier_dir / f"{PE2}.json"
        doc = json.loads(src.read_text())
        doc["dossier"][section]["claims"] = []
        (gate_fixture.dossier_dir / f"{slug}.json").write_text(json.dumps(doc))
        src.unlink()

    def test_no_evidence_exempts_the_member_with_nothing_to_cite(
        self, gate_fixture, split_key_duckdb,
    ):
        """The unlinked member of a shared code: 0 awards on its own account,
        0 lobbying rows on the code, and a bare-keyed concentration figure
        that describes only its sibling's links. Nothing exists for a players
        claim to cite, so empty is honest — and the gate names the page."""
        self._slug_dossier_with_empty_section(gate_fixture, f"{PE2}-SCN")
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert rs["ok"], rs
        assert rs["no_evidence_exempt"] == [f"{PE2}-SCN"]
        assert "nothing to cite" in rs["note"]
        assert f"{PE2}-SCN" in rs["note"]

    def test_no_evidence_does_not_exempt_the_linked_sibling(
        self, gate_fixture, split_key_duckdb,
    ):
        """THE PROOF IT CAN FAIL, and the one that matters: same warehouse,
        same shared code, but this member publishes the links. Its empty
        players section is a real content gap and must still fail."""
        self._slug_dossier_with_empty_section(gate_fixture, f"{PE2}-OPN")
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert not rs["ok"]
        # Labelled by the PAGE, not the code: "3010: players" does not say
        # which of two member pages failed.
        assert f"{PE2}-OPN: players" in rs["empty"]
        assert rs["no_evidence_exempt"] == []

    def test_the_evidence_query_is_page_keyed_not_bare_keyed(
        self, split_key_duckdb,
    ):
        """The keying bug itself, at the unit: the bare pe_bli answers the
        UNION of both members, so it denied the exception to a page that
        publishes nothing. The bare key is also the disambiguation stub — not
        a member page at all — and can never be granted."""
        no_ev = gate_module._has_no_players_evidence
        assert no_ev(split_key_duckdb, PE2, f"{PE2}-SCN") is True
        assert no_ev(split_key_duckdb, PE2, f"{PE2}-OPN") is False
        assert no_ev(split_key_duckdb, PE2) is False
        assert no_ev(split_key_duckdb, PE2, f"{PE2}-NOPE") is False

    def test_the_evidence_query_is_page_keyed_on_an_organization_split_code(
        self, tmp_path,
    ):
        """The ORGANIZATION axis of the same rule (the three #45 codes, e.g.
        '20' = DCSA and DTRA under ONE account, 0300D). An account cannot
        tell these members apart, so the awards filter keys on organization:
        the member with no links of its own is exempt, its linked sibling is
        not."""
        db = tmp_path / "org_split.duckdb"
        con = duckdb.connect(str(db))
        con.execute("create table dim_programs (pe_bli varchar, account varchar,"
                    " account_title varchar, org varchar, exhibit_family varchar)")
        for org in ("DCSA", "DTRA"):
            con.execute("insert into dim_programs values (?,?,?,?,?)",
                        ["20", "0300D", "Procurement, Defense-Wide", org,
                         "procurement"])
        con.execute("create table fct_budget_to_awards (pe_bli varchar,"
                    " account varchar, organization varchar, award_piid varchar)")
        con.execute("insert into fct_budget_to_awards values (?,?,?,?)",
                    ["20", "0300D", "DTRA", "HDTRA1-0001"])
        con.execute("create table fct_program_lobbying (pe_bli varchar,"
                    " family_key varchar, evidence_kind varchar)")
        con.execute("create table fct_program_concentration (pe_bli varchar,"
                    " hhi_all double)")
        con.close()
        no_ev = gate_module._has_no_players_evidence
        assert no_ev(db, "20", "20-DCSA") is True
        assert no_ev(db, "20", "20-DTRA") is False
        assert no_ev(db, "20") is False
        # R-DEC-DOSSIER on this axis too: '20' carried 22 pe_literal rows
        # (bill numbers, not budget lines) that R-INT-9 withholds from both
        # members, so they neither deny DCSA nor excuse DTRA.
        con = duckdb.connect(str(db))
        con.execute("insert into fct_program_lobbying values (?,?,?)",
                    ["20", "LOCKHEED", "pe_literal"])
        con.close()
        assert no_ev(db, "20", "20-DCSA") is True
        assert no_ev(db, "20", "20-DTRA") is False
        assert no_ev(db, "20") is False

    # -----------------------------------------------------------------------
    # R-DEC-DOSSIER (controller ruling, 2026-09-26). fct_program_lobbying is
    # keyed on the BARE code. On a shared (split) code R-INT-9 withholds every
    # such row from every member page — no row can say which member it
    # describes — so the row is not this member's to cite and does NOT deny
    # the empty-players exemption. On a NON-shared code the bare code IS the
    # page, the row renders there, and it still denies the exemption.
    # Production's trigger: chain G step 7 put 1 RTX row on bare '3050'
    # (filing d32fd6e6-…), and 3050-SCN — 0 awards on its own account, a
    # concentration figure that is its sibling's — failed 5b3 over it.
    #   a. the 3050-SCN shape (shared, bare row, nothing of its own) -> EXEMPT
    #   b. the linked sibling on the same code, same bare row        -> FAILS
    #   c. a NON-shared code with a bare row and empty players       -> FAILS
    #   d. the unit test, all identities + the bare stub
    #   e. a missing lobbying mart is still unknown -> never granted
    # -----------------------------------------------------------------------

    @staticmethod
    def _lobbying_row(db, pe_bli, family_key="RTX", evidence_kind="multi_token"):
        con = duckdb.connect(str(db))
        con.execute("insert into fct_program_lobbying values (?,?,?)",
                    [pe_bli, family_key, evidence_kind])
        con.close()

    def test_a_bare_code_lobbying_row_on_a_shared_code_does_not_deny_the_unlinked_member(
        self, gate_fixture, split_key_duckdb,
    ):
        """(a) The 3050-SCN shape exactly: shared code, one bare-code
        lobbying row, no award link on this member's account, a concentration
        figure that describes only the sibling's links. The row is withheld
        from this page (R-INT-9) and is not attributable to it, so the page
        still has nothing to cite: exempt, and named."""
        self._lobbying_row(split_key_duckdb, PE2)
        self._slug_dossier_with_empty_section(gate_fixture, f"{PE2}-SCN")
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert rs["ok"], rs
        assert rs["no_evidence_exempt"] == [f"{PE2}-SCN"]

    def test_a_bare_code_lobbying_row_does_not_excuse_the_linked_sibling(
        self, gate_fixture, split_key_duckdb,
    ):
        """(b) A shared-code member with awards of its own still needs
        players: ignoring a withheld row never excuses a page that DOES have
        something to cite."""
        self._lobbying_row(split_key_duckdb, PE2)
        self._slug_dossier_with_empty_section(gate_fixture, f"{PE2}-OPN")
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert not rs["ok"]
        assert f"{PE2}-OPN: players" in rs["empty"]
        assert rs["no_evidence_exempt"] == []

    def test_a_bare_code_lobbying_row_on_a_non_shared_code_denies_the_exception(
        self, gate_fixture, split_key_duckdb,
    ):
        """(c) THE PROOF IT CAN STILL FAIL on the lobbying axis. PE names one
        program: no awards, no concentration row — exempt on its own — but a
        bare-code row on a NON-shared code is this page's row (the exporter
        publishes it there), so empty players fails. The pair proves the row
        is what decides."""
        path = gate_fixture.dossier_dir / f"{PE}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert rs["ok"], rs
        assert rs["no_evidence_exempt"] == [PE]

        self._lobbying_row(split_key_duckdb, PE, "RAYTHEON", "pe_literal")
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert not rs["ok"]
        assert f"{PE}: players" in rs["empty"]
        assert rs["no_evidence_exempt"] == []

    def test_the_lobbying_axis_at_the_unit_is_shared_code_aware(
        self, split_key_duckdb,
    ):
        """(d) Same row set, every identity: the shared code's unlinked
        member stays exempt, its linked sibling and the bare disambiguation
        stub never are, and the ordinary program is denied by its own row."""
        self._lobbying_row(split_key_duckdb, PE2)
        self._lobbying_row(split_key_duckdb, PE, "RAYTHEON", "pe_literal")
        no_ev = gate_module._has_no_players_evidence
        assert no_ev(split_key_duckdb, PE2, f"{PE2}-SCN") is True
        assert no_ev(split_key_duckdb, PE2, f"{PE2}-OPN") is False
        assert no_ev(split_key_duckdb, PE2) is False
        assert no_ev(split_key_duckdb, PE) is False

    def test_a_missing_lobbying_mart_is_never_granted_even_on_a_shared_code(
        self, split_key_duckdb,
    ):
        """(e) The ruling decides what a PRESENT row means; it does not make
        the mart optional. With fct_program_lobbying absent the answer is
        unknown, and unknown is never granted — on any member."""
        con = duckdb.connect(str(split_key_duckdb))
        con.execute("drop table fct_program_lobbying")
        con.close()
        no_ev = gate_module._has_no_players_evidence
        assert no_ev(split_key_duckdb, PE2, f"{PE2}-SCN") is False
        assert no_ev(split_key_duckdb, PE) is False

    def test_a_non_split_programs_own_concentration_row_denies_the_exception(
        self, gate_fixture, split_key_duckdb,
    ):
        """The member test applies to SHARED codes only. PE names one
        program, so its bare-keyed concentration figure is its own and there
        IS something to cite: empty players fails. Without that row (and with
        no awards or lobbying) the same page is exempt — the pair proves the
        row is what decides."""
        path = gate_fixture.dossier_dir / f"{PE}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        path.write_text(json.dumps(doc))
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        assert res["checks"]["required_sections"]["ok"], (
            res["checks"]["required_sections"])

        con = duckdb.connect(str(split_key_duckdb))
        con.execute("insert into fct_program_concentration (pe_bli, hhi_all)"
                    " values (?,?)", [PE, 2500.0])
        con.close()
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert not rs["ok"]
        assert f"{PE}: players" in rs["empty"]

    def test_no_duckdb_path_cannot_grant_the_no_evidence_exception(
        self, gate_fixture,
    ):
        """Same discipline as built_site_dir: with no warehouse to query the
        exception cannot be granted at all, and the unconditional failure
        applies. Absence is never assumed."""
        self._slug_dossier_with_empty_section(gate_fixture, f"{PE2}-SCN")
        res = _run_gate(gate_fixture)  # no duckdb_path kwarg
        rs = res["checks"]["required_sections"]
        assert not rs["ok"]
        assert f"{PE2}-SCN: players" in rs["empty"]

    def test_the_no_evidence_exception_is_players_only(
        self, gate_fixture, split_key_duckdb,
    ):
        """A page with no contractor evidence still has to say what it is:
        every other empty required section fails exactly as before."""
        self._slug_dossier_with_empty_section(
            gate_fixture, f"{PE2}-SCN", section="what_it_is")
        res = _run_gate(gate_fixture, duckdb_path=split_key_duckdb)
        rs = res["checks"]["required_sections"]
        assert not rs["ok"]
        assert f"{PE2}-SCN: what_it_is" in rs["empty"]

    def test_missing_dossier_file_fails(self, gate_fixture):
        (gate_fixture.dossier_dir / f"{PE2}.json").unlink()
        res = _run_gate(gate_fixture)
        assert not res["checks"]["dossiers_present"]["ok"]
        assert res["checks"]["dossiers_present"]["missing"] == [PE2]

    def test_missing_category_row_fails(self, gate_fixture, site_fixture):
        site_fixture.categories.write_text(
            "pe_bli,category,rationale,source_ref\n"
            f"{PE},default,broad portfolio,ProgramElement[5]\n")
        res = _run_gate(gate_fixture)
        assert not res["checks"]["categories"]["ok"]
        assert res["checks"]["categories"]["missing"] == [PE2]

    def test_bad_category_source_ref_fails(self, gate_fixture, site_fixture):
        site_fixture.categories.write_text(
            "pe_bli,category,rationale,source_ref\n"
            f"{PE},default,broad portfolio,https://example.com/not-a-ref\n"
            f"{PE2},hypersonics,hypersonic tech,snapshot:{SHA}\n")
        res = _run_gate(gate_fixture)
        cats = res["checks"]["categories"]
        assert not cats["ok"]
        assert any("unresolvable source_ref" in e for e in cats["errors"])

    def test_structure_error_fails(self, gate_fixture):
        (gate_fixture.dossier_dir / f"{PE}.json").write_text(json.dumps({
            "pe_bli": PE, "dossier": {"what_it_is": {"claims": []}}}))
        res = _run_gate(gate_fixture)
        assert not res["checks"]["structure"]["ok"]

    def test_pre_batch_assertion(self, gate_fixture):
        res = pre_batch_check([PE, PE2, "0699ROGUE"], {PE, PE2})
        assert not res["ok"]
        assert res["missing"] == ["0699ROGUE"]
        ok = pre_batch_check([PE, PE2], {PE, PE2})
        assert ok["ok"] and ok["count"] == 2

    def test_gate_includes_pre_batch_when_dim_programs_given(self, gate_fixture):
        gate_fixture.dim_pe = {PE}  # PE2 missing from dim_programs
        res = _run_gate(gate_fixture)
        assert not res["checks"]["pre_batch"]["ok"]
        assert not res["ok"]


class TestSourceRefResolvable:
    SHAS = {SHA}

    def test_snapshot_ref(self):
        assert source_ref_resolvable(f"snapshot:{SHA}", self.SHAS)
        assert not source_ref_resolvable("snapshot:" + "0" * 64, self.SHAS)

    def test_xml_path(self):
        assert source_ref_resolvable("ProgramElement[5]", set())
        assert source_ref_resolvable("ProgramElement[0]/Project[4]", set())
        assert not source_ref_resolvable("ProgramElement", set())

    def test_jbook_ref(self):
        assert source_ref_resolvable("jbook:0601101E:ProgramElement[2]", set())
        assert not source_ref_resolvable("jbook:0601101E:", set())

    def test_lda_ref(self):
        assert source_ref_resolvable(
            "lda:25010ccf-ae87-4723-91e0-ed906eeb69a8", set())
        assert not source_ref_resolvable("lda:nope", set())

    def test_garbage(self):
        assert not source_ref_resolvable("", set())
        assert not source_ref_resolvable("https://example.com", set())


# ---------------------------------------------------------------------------
# build_requests (recon §G shape, no network)
# ---------------------------------------------------------------------------


class TestBuildRequests:
    def test_request_shape(self):
        reqs = build_requests([{"pe_bli": PE, "title": "T", "text": "BUNDLE"}])
        assert len(reqs) == 1
        r = reqs[0]
        assert r["custom_id"] == f"dossier-{PE}"
        p = r["params"]
        assert p["model"] == MODEL
        assert p["max_tokens"] == MAX_OUTPUT_TOKENS
        assert p["messages"] == [{"role": "user", "content": "BUNDLE"}]
        assert p["output_config"]["format"]["type"] == "json_schema"
        assert p["system"][0]["cache_control"]["ttl"] == "1h"


def test_submit_pe_blis_filter_unknown_aborts(monkeypatch, tmp_path):
    """--pe-blis outside the top-N set must abort loudly, never submit nothing."""
    import pytest

    from govbudget.dossiers import batch as B

    monkeypatch.setattr(B, "require_client", lambda c=None: object())
    monkeypatch.setattr(
        B, "top50", None, raising=False
    )  # not used directly; patched via research below
    import govbudget.dossiers.research as R

    monkeypatch.setattr(
        R, "top50", lambda db, limit=50: [("0601101E", "t", "DARPA", 1.0)]
    )
    with pytest.raises(SystemExit, match="not in the"):
        B.submit(
            duckdb_path="x",
            site_json_dir=tmp_path,
            snapshots_dir=tmp_path,
            categories_csv=tmp_path / "c.csv",
            raw_dir=tmp_path,
            client=object(),
            pe_blis=["NOT_A_REAL_PE"],
        )


# ---------------------------------------------------------------------------
# verify_phase5b3: PROOF-IT-CAN-FAIL for the real dossier gate
# ---------------------------------------------------------------------------
# These tests exercise the wiring in verify_phase5b3._run_real_gate via the
# underlying govbudget.dossiers.gate.dossier_gate function directly.
# The exact bug: url='ProgramElement[0]' is an xml anchor, not a snapshot URL.
# The vacuous file-presence gate passed it; the real gate must fail it.


def _make_verify_fixture(tmp_path: Path, *, snap_url: str | None = None):
    """Minimal fixture that mirrors the real data layout."""
    dossier_dir = tmp_path / "dossiers"
    dossier_dir.mkdir(parents=True)
    citations_dir = tmp_path
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()
    categories_csv = tmp_path / "program_categories.csv"

    fact_ids = {"real-fact-abc": {"kind": "derived"}}
    (citations_dir / "citations.json").write_text(json.dumps(fact_ids))

    # snapshot index: optionally contains the test URL
    if snap_url is not None:
        snap_sha = "aa" * 32
        (snapshots_dir / "index.json").write_text(json.dumps({"snapshots": [
            {"sha256": snap_sha, "url": snap_url,
             "retrieved_at": "2026-06-01T00:00:00Z",
             "title": "Test snapshot", "pe_bli": PE, "matched_term": "test"},
        ]}))
    else:
        (snapshots_dir / "index.json").write_text(json.dumps({"snapshots": []}))

    categories_csv.write_text(
        "pe_bli,category,rationale,source_ref\n"
        f"{PE},default,broad portfolio,ProgramElement[5]\n"
    )

    return SimpleNamespace(
        dossier_dir=dossier_dir,
        citations=citations_dir / "citations.json",
        snapshots_index=snapshots_dir / "index.json",
        categories=categories_csv,
        top50=[(PE, "Test Program", "DARPA", 100.0)],
        dim_pe={PE},
    )


def _anchor_dossier():
    """Dossier where one claim cites url='ProgramElement[0]' (xml anchor, not snapshot)."""
    return {
        "pe_bli": PE, "model": MODEL, "collected_at": "2026-06-01T00:00:00Z",
        "dossier": {
            "what_it_is": {"claims": [
                {"text": "A real claim.", "citation": {"fact_id": "real-fact-abc"}},
                # The bug: model hallucinated an xml anchor as a url citation
                {"text": "A broken claim.", "citation": {"url": "ProgramElement[0]"}},
            ]},
            "why_it_matters": {"claims": [
                {"text": "Real.", "citation": {"fact_id": "real-fact-abc"}},
                {"text": "Real2.", "citation": {"fact_id": "real-fact-abc"}},
                {"text": "Real3.", "citation": {"fact_id": "real-fact-abc"}},
            ]},
            "players": {"claims": [
                {"text": "Real.", "citation": {"fact_id": "real-fact-abc"}},
            ]},
            "recent_developments": {"claims": []},
        },
    }


class TestVerifyPhase5b3DossierGate:
    """Proof-it-can-fail: url='ProgramElement[0]' fails gate; real URL passes."""

    def test_anchor_url_fails_gate(self, tmp_path):
        """PROOF-IT-CAN-FAIL: xml anchor as url → gate FAIL listing the citation."""
        fx = _make_verify_fixture(tmp_path, snap_url=None)
        (fx.dossier_dir / f"{PE}.json").write_text(json.dumps(_anchor_dossier()))

        result = dossier_gate(
            fx.dossier_dir, fx.citations, fx.snapshots_index,
            fx.categories, fx.top50, dim_programs_pe=fx.dim_pe,
        )

        assert not result["ok"], "Gate must FAIL when url is an xml anchor"
        check = result["checks"]["citations_resolvable"]
        assert not check["ok"]
        bad = check["unresolved"]
        assert len(bad) >= 1
        offending = bad[0]
        assert offending["pe_bli"] == PE
        assert offending["section"] == "what_it_is"
        assert offending["url"] == "ProgramElement[0]"

    def test_real_snapshot_url_passes_gate(self, tmp_path):
        """PROOF-IT-CAN-PASS: the same claim with a real snapshot URL passes."""
        real_url = "https://www.defensenews.com/test-article/"
        fx = _make_verify_fixture(tmp_path, snap_url=real_url)

        # Build the dossier but replace the anchor url with the real snapshot url
        doc = _anchor_dossier()
        doc["dossier"]["what_it_is"]["claims"][1]["citation"]["url"] = real_url
        (fx.dossier_dir / f"{PE}.json").write_text(json.dumps(doc))

        result = dossier_gate(
            fx.dossier_dir, fx.citations, fx.snapshots_index,
            fx.categories, fx.top50, dim_programs_pe=fx.dim_pe,
        )

        assert result["checks"]["citations_resolvable"]["ok"], (
            f"citations_resolvable should PASS with a real snapshot url; "
            f"unresolved={result['checks']['citations_resolvable'].get('unresolved')}"
        )

    def test_blocked_path_unchanged(self, tmp_path):
        """BLOCKED path: dossier dir absent → _dossier_blocked returns a BLOCKED dict."""
        from govbudget.verify_phase5b3 import _dossier_blocked
        site_json_dir = tmp_path / "site" / "json"
        site_json_dir.mkdir(parents=True)
        # dossiers/ subdir does NOT exist
        result = _dossier_blocked(site_json_dir)
        assert result is not None
        assert result["blocked"] is True
        assert result["ok"] is False
        assert "ANTHROPIC_API_KEY" in result["reason"]

    def test_blocked_path_empty_dir(self, tmp_path):
        """BLOCKED path: dossiers/ exists but empty → _dossier_blocked returns BLOCKED."""
        from govbudget.verify_phase5b3 import _dossier_blocked
        site_json_dir = tmp_path / "site" / "json"
        (site_json_dir / "dossiers").mkdir(parents=True)
        result = _dossier_blocked(site_json_dir)
        assert result is not None
        assert result["blocked"] is True

    def test_blocked_path_present_dir(self, tmp_path):
        """When dossiers are present, _dossier_blocked returns None (gate proceeds)."""
        from govbudget.verify_phase5b3 import _dossier_blocked
        site_json_dir = tmp_path / "site" / "json"
        dossiers_dir = site_json_dir / "dossiers"
        dossiers_dir.mkdir(parents=True)
        (dossiers_dir / "0601101E.json").write_text("{}")
        result = _dossier_blocked(site_json_dir)
        assert result is None


class TestBundleHygieneRound2:
    """Anchor leaks found in the second live batch: category source_ref and
    feed-card internal URLs were rendered into bundles and cited verbatim."""

    def test_category_row_strips_source_ref(self, tmp_path):
        from govbudget.dossiers.batch import _category_row

        csv_path = tmp_path / "cats.csv"
        csv_path.write_text(
            "pe_bli,category,rationale,source_ref\n"
            "0604250D8Z,default,SCO portfolio,ProgramElement[52]\n"
        )
        row = _category_row(csv_path, "0604250D8Z")
        assert row is not None
        assert "source_ref" not in row
        assert "ProgramElement" not in str(row)

    def test_feed_events_strip_internal_urls(self, tmp_path):
        """Through _assemble itself (this used to re-type its selection
        inline, and so stopped mirroring it the day the selection moved from
        the bare pe_bli to the page the card addresses)."""
        import json

        from govbudget.dossiers import batch as B

        site = tmp_path / "json"
        site.mkdir()
        (site / "feed.json").write_text(json.dumps({"cards": [{
            "pe_bli": "0603467E", "headline": "h", "figure_fact_id": "abc",
            "why_url": "/methodology/#feed-x", "program_url": "/program/0603467E/",
        }]}))
        snaps = tmp_path / "snaps"
        snaps.mkdir()
        (snaps / "index.json").write_text(json.dumps({"snapshots": []}))
        cats = tmp_path / "cats.csv"
        cats.write_text("pe_bli,category,rationale,source_ref\n")
        cards = B._assemble(
            "0603467E", site_json_dir=site, snapshots_dir=snaps,
            categories_csv=cats,
        )["feed_events"]
        assert cards and "why_url" not in cards[0] and "program_url" not in cards[0]
        assert cards[0]["figure_fact_id"] == "abc"


# ---------------------------------------------------------------------------
# chain-B fix 3 — the pipeline is keyed by PAGE identity
#
# Measured defect this pins (chain-B fix 2 round 2): `dossiers submit
# --pe-blis 3010-SCN` aborted because the membership set was bare-keyed, and
# the only accepted key ("3010") assembled an EMPTY bundle because
# program_details/3010.json is a disambiguation stub that does not exist. The
# same bundle carried award rows with no fact_id, so no players claim naming
# the five recipients the page publishes could have been cited at all.
# ---------------------------------------------------------------------------

SPLIT_PE = "3010"
SPLIT_SCN, SPLIT_OPN = "3010-SCN", "3010-OPN"
SCN_AWARD_FIDS = [f"scnlink{i}" for i in range(5)]


@pytest.fixture()
def split_site_fixture(tmp_path):
    """A shared BLI code in production's 3010 shape: two member pages, each
    with its own sidecar, and five citable crosswalk links on the SCN member.
    """
    site_json = tmp_path / "json"
    (site_json / "program_details").mkdir(parents=True)
    (site_json / "flows").mkdir()
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()

    (site_json / "programs.json").write_text(json.dumps([
        {"pe_bli": SPLIT_PE, "slug": SPLIT_SCN, "title": "LPD Flight II",
         "org": "N", "account": "1611N"},
        {"pe_bli": SPLIT_PE, "slug": SPLIT_OPN,
         "title": "Shipboard Tactical Communications", "org": "N",
         "account": "1810N"},
        {"pe_bli": PE, "slug": PE, "title": "Defense Research Sciences",
         "org": "DARPA"},
    ]))
    (site_json / "program_details" / f"{SPLIT_SCN}.json").write_text(json.dumps({
        "narratives": [], "mentions": [], "budget_lines": [], "details": [],
        "awards": [
            {"award_piid": f"N000241{i}C2439", "confidence": "medium",
             "recipient_name": f"PRIME {i}", "fact_id": SCN_AWARD_FIDS[i]}
            for i in range(5)
        ],
    }))
    (site_json / "program_details" / f"{SPLIT_OPN}.json").write_text(json.dumps({
        "narratives": [], "mentions": [], "budget_lines": [], "details": [],
        "awards": [{"award_piid": "N0003917D0006", "confidence": "medium",
                    "recipient_name": "OTHER PRIME", "fact_id": "opnlink0"}],
    }))
    # The bare code owns NO sidecar — it is the disambiguation stub.
    (site_json / "program_details" / f"{PE}.json").write_text(json.dumps({
        "narratives": [], "mentions": [], "budget_lines": [], "details": [],
        "awards": [{"award_piid": "W911QX24C0001", "confidence": "high",
                    "recipient_name": "ORDINARY PRIME",
                    "fact_id": "ordinarylink"}],
    }))
    (site_json / "citations.json").write_text(json.dumps(
        {fid: {"kind": "derived"} for fid in SCN_AWARD_FIDS}
        | {"opnlink0": {"kind": "derived"}, "ordinarylink": {"kind": "derived"}}
    ))
    (snapshots / "index.json").write_text(json.dumps({"snapshots": []}))
    categories = tmp_path / "program_categories.csv"
    categories.write_text(
        "pe_bli,category,rationale,source_ref\n"
        f"{SPLIT_PE},shipbuilding,amphibs,ProgramElement[1]\n"
        f"{PE},default,broad portfolio,ProgramElement[5]\n"
    )
    return SimpleNamespace(site_json=site_json, snapshots=snapshots,
                           categories=categories, tmp=tmp_path)


@pytest.fixture()
def split_top50_duckdb(tmp_path):
    """dim_programs/fct_budget_trajectory in the 3010 shape, so top50()
    resolves each member to its own page slug."""
    db = tmp_path / "split-top50.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table dim_programs (pe_bli varchar, org varchar,"
                " exhibit_family varchar, title varchar, account varchar,"
                " account_title varchar)")
    con.execute("create table fct_budget_trajectory (pe_bli varchar,"
                " organization varchar, fy2026_total double, account varchar)")
    con.execute("insert into dim_programs values"
                " ('3010','N','procurement','LPD Flight II','1611N',"
                "  'Shipbuilding and Conversion, Navy'),"
                " ('3010','N','procurement','Shipboard Tactical Communications',"
                "  '1810N','Other Procurement, Navy'),"
                f" ('{PE}','DARPA','rdte','Defense Research Sciences','0400',"
                "  'Research, Development, Test and Evaluation')")
    con.execute("insert into fct_budget_trajectory values"
                " ('3010','N',2600000.0,'1611N'),"
                " ('3010','N',20900.0,'1810N'),"
                f" ('{PE}','DARPA',100.0,'0400')")
    con.close()
    return db


class TestPageIdentityBundles:
    def _build(self, fx, key, **kw):
        return build_bundle(key, site_json_dir=fx.site_json,
                            snapshots_dir=fx.snapshots,
                            categories_csv=fx.categories, **kw)

    def test_a_split_member_slug_assembles_that_members_awards_with_fact_ids(
        self, split_site_fixture
    ):
        """The whole point: the member's own five links, each citable."""
        b = self._build(split_site_fixture, SPLIT_SCN)
        data = _bundle_json(b)
        assert [a["fact_id"] for a in data["awards"]] == SCN_AWARD_FIDS
        assert len(data["awards"]) == 5
        # the bundle knows both identities: the code it belongs to and the
        # page it IS
        assert data["pe_bli"] == SPLIT_PE
        assert data["page"] == SPLIT_SCN
        # the request's key — and therefore the archive and sidecar name — is
        # the page, not the code
        assert b["pe_bli"] == SPLIT_SCN
        assert b["title"] == "LPD Flight II"

    def test_the_sibling_member_gets_its_own_award_not_this_one(
        self, split_site_fixture
    ):
        data = _bundle_json(self._build(split_site_fixture, SPLIT_OPN))
        assert [a["award_piid"] for a in data["awards"]] == ["N0003917D0006"]
        assert data["page"] == SPLIT_OPN

    def test_a_bare_shared_code_is_rejected_and_names_the_member_slugs(
        self, split_site_fixture
    ):
        with pytest.raises(SystemExit) as exc:
            self._build(split_site_fixture, SPLIT_PE)
        msg = str(exc.value)
        assert "SHARED BLI code" in msg
        assert SPLIT_SCN in msg and SPLIT_OPN in msg
        assert "ABORTED" in msg

    def test_an_ordinary_program_is_byte_for_byte_unchanged(
        self, split_site_fixture
    ):
        data = _bundle_json(self._build(split_site_fixture, PE))
        assert data["pe_bli"] == PE and data["page"] == PE
        assert [a["award_piid"] for a in data["awards"]] == ["W911QX24C0001"]

    def test_a_feed_card_reaches_only_the_page_it_addresses(
        self, split_site_fixture
    ):
        """Task 28a publishes a shared code's concentration card under the ONE
        member that carries its links — program_url /program/{member slug}/ —
        while its pe_bli stays the bare code (the guid's and every company
        watchlist's key). Selecting feed cards by pe_bli offered that member's
        per-year HHI, with a resolvable fid, to the sibling's bundle as well:
        the #82 cross-member shape no citation gate sees. A card is selected
        by the page it addresses (export_site._feed_program_key), the key
        /feed/ links it by."""
        fx = split_site_fixture
        (fx.site_json / "feed.json").write_text(json.dumps({"cards": [
            # 28a's member card: keyed on the bare code, addressed to SCN
            {"pe_bli": SPLIT_PE, "event_type": "concentration_shift",
             "figure_fact_id": "scnhhi",
             "program_url": f"/program/{SPLIT_SCN}/",
             "why_url": "/methodology/#feed-concentration_shift"},
            # the pre-28a shape: the bare code's stub, which is no member's
            {"pe_bli": SPLIT_PE, "event_type": "concentration_shift",
             "figure_fact_id": "barehhi",
             "program_url": f"/program/{SPLIT_PE}/"},
            # an ordinary program: a linked card and one with no page link
            {"pe_bli": PE, "event_type": "yoy_swing",
             "figure_fact_id": "ordswing", "program_url": f"/program/{PE}/"},
            {"pe_bli": PE, "event_type": "request_vs_actuals_gap",
             "figure_fact_id": "ordrva", "program_url": None},
            # a company card
            {"pe_bli": None, "family_key": "ACME", "event_type": "new_entrant",
             "figure_fact_id": "acmefact", "program_url": None},
        ]}))

        def events(key):
            return _bundle_json(self._build(fx, key))["feed_events"]

        assert [e["figure_fact_id"] for e in events(SPLIT_SCN)] == ["scnhhi"]
        assert events(SPLIT_OPN) == []
        assert [e["figure_fact_id"] for e in events(PE)] == ["ordswing", "ordrva"]
        # the internal anchors are still stripped from what reaches the model
        assert all(
            "program_url" not in e and "why_url" not in e
            for e in events(SPLIT_SCN) + events(PE)
        )

    def test_an_unresolvable_award_fact_id_is_dropped_not_offered(
        self, split_site_fixture
    ):
        """Hygiene, same rule as projects/narratives: the model may only see a
        fact_id that resolves, or none at all."""
        keyset = set(SCN_AWARD_FIDS[:2])
        data = _bundle_json(
            self._build(split_site_fixture, SPLIT_SCN, citations_keyset=keyset)
        )
        kept = [a.get("fact_id") for a in data["awards"]]
        assert kept[:2] == SCN_AWARD_FIDS[:2]
        assert all(f is None for f in kept[2:])
        for award in data["awards"][2:]:
            assert "fact_id" not in award

    def test_an_award_row_with_no_fact_id_field_survives(self, tmp_path):
        """Older sidecars (pre-chain-B fix 3) carry no fact_id at all — the
        bundle must still assemble, just with nothing citable."""
        site_json = tmp_path / "json"
        (site_json / "program_details").mkdir(parents=True)
        (site_json / "program_details" / f"{PE}.json").write_text(json.dumps(
            {"awards": [{"award_piid": "P1", "confidence": "high",
                         "recipient_name": "V"}]}))
        snaps = tmp_path / "snaps"
        snaps.mkdir()
        (snaps / "index.json").write_text(json.dumps({"snapshots": []}))
        cats = tmp_path / "cats.csv"
        cats.write_text("pe_bli,category,rationale,source_ref\n")
        data = _bundle_json(build_bundle(
            PE, site_json_dir=site_json, snapshots_dir=snaps,
            categories_csv=cats, citations_keyset=set()))
        assert data["awards"] == [{"award_piid": "P1", "confidence": "high",
                                   "recipient_name": "V"}]

    def test_the_preamble_says_award_rows_are_citable(self):
        """Rule 9: without it the model has a fact_id it was never told to
        use, next to a negative rule telling it contract numbers are not
        citations — which is how a page with five named primes shipped a
        dossier naming none."""
        assert "Award recipients:" in SHARED_PREAMBLE
        assert "crosswalk link" in SHARED_PREAMBLE


class TestSubmitPageIdentity:
    def _submit(self, fx, db, client, **kw):
        return submit(
            duckdb_path=db, site_json_dir=fx.site_json,
            snapshots_dir=fx.snapshots, categories_csv=fx.categories,
            raw_dir=fx.tmp / "dossiers-raw", client=client, **kw,
        )

    def test_a_member_slug_is_accepted_and_keys_the_request(
        self, split_site_fixture, split_top50_duckdb
    ):
        client = FakeClient()
        summary = self._submit(split_site_fixture, split_top50_duckdb, client,
                               pe_blis=[SPLIT_SCN])
        assert summary["requests"] == 1
        (requests,) = client.batches.created
        assert [r["custom_id"] for r in requests] == [f"dossier-{SPLIT_SCN}"]
        meta = json.loads((split_site_fixture.tmp / "dossiers-raw"
                           / "batch_meta.json").read_text())
        assert meta["pe_blis"] == [SPLIT_SCN]

    def test_a_bare_shared_code_aborts_naming_the_member_slugs(
        self, split_site_fixture, split_top50_duckdb
    ):
        client = FakeClient()
        with pytest.raises(SystemExit) as exc:
            self._submit(split_site_fixture, split_top50_duckdb, client,
                         pe_blis=[SPLIT_PE])
        msg = str(exc.value)
        assert "SHARED BLI code" in msg
        assert SPLIT_SCN in msg and SPLIT_OPN in msg
        assert "ABORTED" in msg
        assert client.batches.created == []      # nothing was spent

    def test_an_unknown_key_still_aborts_plainly(
        self, split_site_fixture, split_top50_duckdb
    ):
        client = FakeClient()
        with pytest.raises(SystemExit) as exc:
            self._submit(split_site_fixture, split_top50_duckdb, client,
                         pe_blis=["NOSUCHPE"])
        assert "not in the top-50 set" in str(exc.value)
        assert client.batches.created == []

    def test_the_full_batch_keys_every_split_member_by_its_page(
        self, split_site_fixture, split_top50_duckdb
    ):
        client = FakeClient()
        self._submit(split_site_fixture, split_top50_duckdb, client)
        (requests,) = client.batches.created
        assert sorted(r["custom_id"] for r in requests) == [
            f"dossier-{PE}", f"dossier-{SPLIT_OPN}", f"dossier-{SPLIT_SCN}",
        ]

    def test_an_ordinary_corpus_is_unchanged(self, site_fixture,
                                             fixture_duckdb):
        """No page identity in the warehouse -> bare keys, exactly as before."""
        client = FakeClient()
        self._submit(site_fixture, fixture_duckdb, client)
        (requests,) = client.batches.created
        assert sorted(r["custom_id"] for r in requests) == [
            f"dossier-{PE}", f"dossier-{PE2}"]


class TestGatePageIdentity:
    def test_the_gate_asks_for_the_page_the_selection_picked(self, tmp_path):
        """A split member's dossier is filed under its page slug; the gate
        looks for exactly that, from top50()'s own 5th element."""
        dossier_dir = tmp_path / "dossiers"
        dossier_dir.mkdir()
        (dossier_dir / f"{SPLIT_SCN}.json").write_text(json.dumps(
            {"pe_bli": SPLIT_PE, "slug": SPLIT_SCN,
             "dossier": _valid_dossier(url_claims=0, fact_claims=3)}))
        (tmp_path / "citations.json").write_text(json.dumps(
            {f: {"kind": "derived"} for f in
             ["traj26fact", "hhifact", "blfact", "feedfact", "detfact0"]}))
        (tmp_path / "snap-index.json").write_text(json.dumps({"snapshots": []}))
        cats = tmp_path / "cats.csv"
        cats.write_text("pe_bli,category,rationale,source_ref\n"
                        f"{SPLIT_PE},shipbuilding,amphibs,ProgramElement[1]\n")
        res = dossier_gate(
            dossier_dir, tmp_path / "citations.json",
            tmp_path / "snap-index.json", cats,
            [(SPLIT_PE, "LPD Flight II", "N", 1.0, SPLIT_SCN)],
        )
        assert res["checks"]["dossiers_present"]["ok"], res["checks"]
        assert res["checks"]["required_sections"]["ok"]

    def test_a_missing_member_dossier_still_reads_as_missing(self, tmp_path):
        """And it is reported by the PAGE that is missing, not by the code
        (ROADMAP #82, 2026-09-12): "3010" does not say which of two member
        pages the operator has to regenerate."""
        dossier_dir = tmp_path / "dossiers"
        dossier_dir.mkdir()
        (tmp_path / "citations.json").write_text(json.dumps({}))
        (tmp_path / "snap-index.json").write_text(json.dumps({"snapshots": []}))
        cats = tmp_path / "cats.csv"
        cats.write_text("pe_bli,category,rationale,source_ref\n")
        res = dossier_gate(
            dossier_dir, tmp_path / "citations.json",
            tmp_path / "snap-index.json", cats,
            [(SPLIT_PE, "LPD Flight II", "N", 1.0, SPLIT_SCN)],
        )
        assert res["checks"]["dossiers_present"]["missing"] == [SPLIT_SCN]

    def test_a_sibling_on_disk_never_answers_for_the_page_asked_for(
        self, tmp_path,
    ):
        """ROADMAP #82 (2026-09-12): the sibling glob is a fallback for
        callers whose selection carries NO page identity. When the selection
        named 3010-SCN, the lone 3010-OPN.json on disk is the OTHER program's
        dossier — accepting it would gate one page against the other page's
        claims, which is the substitution this leg exists to catch."""
        dossier_dir = tmp_path / "dossiers"
        dossier_dir.mkdir()
        (dossier_dir / f"{SPLIT_OPN}.json").write_text(json.dumps(
            {"pe_bli": SPLIT_PE, "slug": SPLIT_OPN,
             "dossier": _valid_dossier(url_claims=0, fact_claims=3)}))
        (tmp_path / "citations.json").write_text(json.dumps(
            {f: {"kind": "derived"} for f in
             ["traj26fact", "hhifact", "blfact", "feedfact", "detfact0"]}))
        (tmp_path / "snap-index.json").write_text(json.dumps({"snapshots": []}))
        cats = tmp_path / "cats.csv"
        cats.write_text("pe_bli,category,rationale,source_ref\n"
                        f"{SPLIT_PE},shipbuilding,amphibs,ProgramElement[1]\n")
        res = dossier_gate(
            dossier_dir, tmp_path / "citations.json",
            tmp_path / "snap-index.json", cats,
            [(SPLIT_PE, "LPD Flight II", "N", 1.0, SPLIT_SCN)],
        )
        assert res["checks"]["dossiers_present"]["missing"] == [SPLIT_SCN]

    def test_the_sibling_glob_still_answers_an_identityless_selection(
        self, tmp_path,
    ):
        """The other half of the same rule: a caller that passed a bare code
        (older fixtures, a hand-run gate) named no page, so exactly one
        "{pe}-{CODE}.json" on disk is still the honest answer."""
        dossier_dir = tmp_path / "dossiers"
        dossier_dir.mkdir()
        (dossier_dir / f"{SPLIT_SCN}.json").write_text(json.dumps(
            {"pe_bli": SPLIT_PE, "slug": SPLIT_SCN,
             "dossier": _valid_dossier(url_claims=0, fact_claims=3)}))
        (tmp_path / "citations.json").write_text(json.dumps(
            {f: {"kind": "derived"} for f in
             ["traj26fact", "hhifact", "blfact", "feedfact", "detfact0"]}))
        (tmp_path / "snap-index.json").write_text(json.dumps({"snapshots": []}))
        cats = tmp_path / "cats.csv"
        cats.write_text("pe_bli,category,rationale,source_ref\n"
                        f"{SPLIT_PE},shipbuilding,amphibs,ProgramElement[1]\n")
        res = dossier_gate(
            dossier_dir, tmp_path / "citations.json",
            tmp_path / "snap-index.json", cats,
            [SPLIT_PE],
        )
        assert res["checks"]["dossiers_present"]["ok"], res["checks"]


# ---------------------------------------------------------------------------
# Ruling R-DEC-DOSSIERDRIFT (controller, 2026-09-26): the gate FAILS any
# PUBLISHED claim that contradicts its cited fact — the same checks the
# exporter withholds on (govbudget.dossiers.claim_drift). Proof it can fail
# uses the two chain-G DARPA shapes verbatim: /program/0602025E/'s "about
# 389" low-concentration claim vs HHI 1,284.683, and /program/0603467E/'s
# "top recipient family ... is Raytheon" vs the cited row's GENERAL DYNAMICS.
# ---------------------------------------------------------------------------

_DRIFT_389 = (
    "Award dollars are spread across 189 recipient families, producing a low"
    " concentration score (Herfindahl-Hirschman Index of about 389), which"
    " indicates a relatively diverse contractor base overall."
)
_DRIFT_TOP = "The top recipient family across the program's award history is Raytheon."
_DRIFT_RAYTHEON = (
    "Across the program's award history, the leading recipient family by dollars"
    " is RAYTHEON, measured over roughly $4.68 billion in program dollars."
)


class TestGateClaimsAgreeWithCitations:
    @staticmethod
    def _cite(fx, rows: dict) -> None:
        cits = json.loads(fx.citations.read_text())
        cits.update(rows)
        fx.citations.write_text(json.dumps(cits))

    @staticmethod
    def _set_players(fx, pe: str, claims: list[dict]) -> None:
        path = fx.dossier_dir / f"{pe}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = claims
        path.write_text(json.dumps(doc))

    @staticmethod
    def _conc_duckdb(tmp_path, family: str, hhi: float, links=()):
        """The marts both claim-drift indexes read (round 2 fails closed on
        a supplied mart missing any of them): PE's concentration row, and
        PE's linked awards as (recipient_name, uei, family_key)."""
        db = tmp_path / "conc.duckdb"
        con = duckdb.connect(str(db))
        con.execute("create table fct_program_concentration (pe_bli varchar,"
                    " hhi_all double, top_family_all varchar, hhi_high double,"
                    " top_family_high varchar)")
        con.execute("insert into fct_program_concentration values (?,?,?,?,?)",
                    [PE, hhi, family, None, None])
        con.execute("create table dim_entities (family_key varchar,"
                    " display_name varchar)")
        con.execute("create table dim_programs (pe_bli varchar, account varchar,"
                    " account_title varchar, org varchar, exhibit_family varchar)")
        con.execute("insert into dim_programs values (?,?,?,?,?)",
                    [PE, None, None, "DARPA", "rdte"])
        con.execute("create table fct_budget_to_awards (pe_bli varchar,"
                    " account varchar, organization varchar, award_piid varchar,"
                    " recipient_name varchar, recipient_uei varchar)")
        con.execute("create table entity_xwalk (recipient_uei varchar,"
                    " recipient_name varchar, parent_name varchar, family_key varchar)")
        for i, (name, uei, fam) in enumerate(links):
            con.execute("insert into fct_budget_to_awards values (?,?,?,?,?,?)",
                        [PE, None, "DARPA", f"HR{i}", name, uei])
            con.execute("insert into entity_xwalk values (?,?,?,?)", [uei, name, None, fam])
        con.close()
        return db

    def _hhi_fid(self):
        from govbudget.export_site import fact_id_derived
        return fact_id_derived("concentration", PE, "hhi")

    def test_a_published_hhi_claim_contradicting_its_fact_fails(self, gate_fixture):
        fid = self._hhi_fid()
        self._cite(gate_fixture, {fid: {"kind": "derived", "units": "Herfindahl-Hirschman Index",
                                        "recorded_value": "1284.683"}})
        self._set_players(gate_fixture, PE, [
            {"text": _DRIFT_389, "citation": {"fact_id": fid}}])
        res = _run_gate(gate_fixture)
        check = res["checks"]["claims_agree_with_citations"]
        assert not check["ok"] and not res["ok"]
        [bad] = check["contradictions"]
        assert bad["page"] == PE and bad["section"] == "players" and bad["claim"] == 0
        assert bad["fact_id"] == fid and bad["cited_value"] == "1284.683"
        assert bad["reasons"] == ["stated_figure", "concentration_band"]
        assert "about 389" in check["note"]

    def test_a_top_family_claim_naming_the_wrong_family_fails(self, gate_fixture, tmp_path):
        fid = self._hhi_fid()
        self._cite(gate_fixture, {fid: {"kind": "derived", "units": "Herfindahl-Hirschman Index",
                                        "recorded_value": "4831.486"}})
        self._set_players(gate_fixture, PE, [
            {"text": _DRIFT_TOP, "citation": {"fact_id": fid}}])
        db = self._conc_duckdb(tmp_path, "GENERAL DYNAMICS", 4831.486)
        res = _run_gate(gate_fixture, duckdb_path=db)
        check = res["checks"]["claims_agree_with_citations"]
        assert not check["ok"]
        assert check["family_check"] is True
        assert [c["reasons"] for c in check["contradictions"]] == [["top_family"]]

    def test_without_the_mart_the_family_leg_is_reported_not_run(self, gate_fixture):
        fid = self._hhi_fid()
        self._cite(gate_fixture, {fid: {"kind": "derived", "units": "Herfindahl-Hirschman Index",
                                        "recorded_value": "4831.486"}})
        self._set_players(gate_fixture, PE, [
            {"text": _DRIFT_TOP, "citation": {"fact_id": fid}}])
        res = _run_gate(gate_fixture)
        check = res["checks"]["claims_agree_with_citations"]
        assert check["family_check"] is False
        assert check["ok"]

    def test_a_true_claim_passes(self, gate_fixture, tmp_path):
        fid = self._hhi_fid()
        self._cite(gate_fixture, {fid: {"kind": "derived", "units": "Herfindahl-Hirschman Index",
                                        "recorded_value": "1284.683"}})
        self._set_players(gate_fixture, PE, [{
            "text": "SYSTEM HIGH is the top recipient family; award dollars are"
                    " moderately concentrated (HHI of about 1,285).",
            "citation": {"fact_id": fid}}])
        db = self._conc_duckdb(tmp_path, "SYSTEM HIGH", 1284.683)
        res = _run_gate(gate_fixture, duckdb_path=db)
        assert res["checks"]["claims_agree_with_citations"]["ok"], res["checks"]
        assert res["ok"]

    def test_the_exporters_output_passes_and_its_emptied_section_needs_disclosure(
        self, gate_fixture, site_fixture, tmp_path,
    ):
        """End to end: the exporter withholds the contradicting claims; the
        gate then finds nothing published to fail on. The withheld claims
        were PE's whole players section, so the section is empty — and the
        emptied-section exception still demands BOTH the sidecar's own drop
        record AND a built page that discloses it (never granted on the
        sidecar's say-so)."""
        from govbudget.export_site import _emit_dossier_sidecars, fact_id_derived

        hhi_fid = self._hhi_fid()
        dollars_fid = fact_id_derived("concentration", PE, "program_dollars")
        self._cite(gate_fixture, {
            hhi_fid: {"kind": "derived", "units": "Herfindahl-Hirschman Index",
                      "recorded_value": "1284.683"},
            dollars_fid: {"kind": "derived", "units": "USD",
                          "recorded_value": "469988662.800"},
        })
        raw_dir = tmp_path / "dossiers-raw"
        raw_dir.mkdir()
        for pe in (PE, PE2):
            doc = json.loads((gate_fixture.dossier_dir / f"{pe}.json").read_text())
            if pe == PE:
                doc["dossier"]["players"]["claims"] = [
                    {"text": _DRIFT_RAYTHEON, "citation": {"fact_id": dollars_fid}},
                    {"text": _DRIFT_389, "citation": {"fact_id": hhi_fid}},
                ]
            (raw_dir / f"{pe}.json").write_text(json.dumps({
                "custom_id": f"dossier-{pe}", "collected_at": "2026-07-02T00:00:00Z",
                "message": {"model": MODEL, "content": [
                    {"type": "text", "text": json.dumps(doc["dossier"])}]},
            }))
        cits = json.loads(gate_fixture.citations.read_text())
        db = self._conc_duckdb(tmp_path, "SYSTEM HIGH", 1284.683)
        from govbudget.dossiers.claim_drift import (
            concentration_fact_index,
            linked_recipient_index,
        )
        summary = _emit_dossier_sidecars(
            json_dir=gate_fixture.dossier_dir.parent,
            dossiers_raw_dir=raw_dir,
            citations_keyset=set(cits),
            snapshot_urls={SNAP_URL},
            fact_id_to_recorded_value={k: v["recorded_value"] for k, v in cits.items()
                                       if v.get("recorded_value") is not None},
            citation_facts=cits,
            concentration_facts=concentration_fact_index(db),
            linked_recipients=linked_recipient_index(db),
        )
        assert summary["withheld_by_pe"] == {PE: 2}

        res = _run_gate(gate_fixture, duckdb_path=db)
        assert res["checks"]["claims_agree_with_citations"]["ok"]
        # players emptied by withholding: no built page -> still FAILS
        assert f"{PE}: players" in res["checks"]["required_sections"]["empty"]
        assert not res["ok"]

        built = site_fixture.tmp / "out"
        (built / "program" / PE).mkdir(parents=True)
        # round 1 wrote a subjectless note here; round 2's disclosure check
        # reads the note back against the sidecar's dropped_reasons, so a
        # note that does not say the TRUE reason no longer discloses the drop
        page = built / "program" / PE / "index.html"
        page.write_text(
            '<p data-dossier-dropped-claims="2">2 claims removed: did not meet the'
            " evidence standard.</p>")
        res = _run_gate(gate_fixture, duckdb_path=db, built_site_dir=built)
        assert f"{PE}: players" in res["checks"]["required_sections"]["empty"]
        page.write_text(
            '<p class="text-sm" data-dossier-dropped-claims="2">2<!-- --> claim<!-- -->s'
            "<!-- --> removed:<!-- --> <!-- -->they stated figures, years or recipients their"
            " sources do not support<!-- -->.</p>")
        res = _run_gate(gate_fixture, duckdb_path=db, built_site_dir=built)
        assert res["checks"]["required_sections"]["ok"], res["checks"]["required_sections"]
        assert res["checks"]["claims_agree_with_citations"]["ok"]


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERDRIFT round 2 (2026-09-26) in the gate: fail closed on a
# supplied mart it cannot read; recipient lists; and a disclosure check that
# reads the Correction note's REASONS back against the sidecar, not only its
# count.
# ---------------------------------------------------------------------------

_DRIFT_RECIPIENTS = (
    "Recorded recipients of awards linked to the program include Booz Allen"
    " Hamilton, The Johns Hopkins University Applied Physics Laboratory, Leidos,"
    " Raytheon Company, Lockheed Martin Corporation, Northrop Grumman Systems"
    " Corp, SRI International, and the Massachusetts Institute of Technology."
)


class TestGateDriftRound2:
    _cite = staticmethod(TestGateClaimsAgreeWithCitations._cite)
    _set_players = staticmethod(TestGateClaimsAgreeWithCitations._set_players)
    _conc_duckdb = staticmethod(TestGateClaimsAgreeWithCitations._conc_duckdb)

    def test_an_unreadable_mart_is_an_error_not_a_leg_not_run(self, gate_fixture, tmp_path):
        """Round 1 turned any read failure into {} and passed with the note
        "top-family leg not run". A path WAS given: that is a failure."""
        db = tmp_path / "narrow.duckdb"
        con = duckdb.connect(str(db))
        con.execute("create table fct_program_concentration (pe_bli varchar, hhi_all double)")
        con.close()
        res = _run_gate(gate_fixture, duckdb_path=db)
        check = res["checks"]["claims_agree_with_citations"]
        assert not check["ok"] and not res["ok"]
        assert check["error"] and "fct_program_concentration" in check["error"]
        assert check["family_check"] is False and check["recipient_check"] is False
        assert "legs not run: no mart" not in check["note"] and "ERROR" in check["note"]

    def test_a_missing_mart_file_is_an_error(self, gate_fixture, tmp_path):
        res = _run_gate(gate_fixture, duckdb_path=tmp_path / "absent.duckdb")
        check = res["checks"]["claims_agree_with_citations"]
        assert not check["ok"] and check["error"]

    def test_no_mart_at_all_still_reports_the_legs_not_run(self, gate_fixture):
        check = _run_gate(gate_fixture)["checks"]["claims_agree_with_citations"]
        assert check["ok"] and check["error"] is None
        assert check["family_check"] is False and check["recipient_check"] is False
        assert "not run" in check["note"]

    def test_a_recipient_list_naming_unlinked_recipients_fails(self, gate_fixture, tmp_path):
        from govbudget.export_site import fact_id_derived

        fid = fact_id_derived("concentration", PE, "program_dollars")
        self._cite(gate_fixture, {fid: {"kind": "derived", "units": "USD",
                                        "recorded_value": "74376328.830"}})
        self._set_players(gate_fixture, PE, [
            {"text": _DRIFT_RECIPIENTS, "citation": {"fact_id": fid}}])
        db = self._conc_duckdb(tmp_path, "GENERAL DYNAMICS", 4831.486, links=[
            ("RAYTHEON COMPANY", "UEI-RAY", "RAYTHEON"),
            ("NORTHROP GRUMMAN SYSTEMS CORP", "UEI-NG", "NORTHROP GRUMMAN"),
            ("APPLIED PHYSICAL SCIENCES CORP", "UEI-APS", "GENERAL DYNAMICS"),
        ])
        res = _run_gate(gate_fixture, duckdb_path=db)
        check = res["checks"]["claims_agree_with_citations"]
        assert not check["ok"] and check["recipient_check"] is True
        [bad] = check["contradictions"]
        assert bad["reasons"] == ["recipient_list"]
        assert bad["unlinked_recipients"] == [
            "Booz Allen Hamilton", "The Johns Hopkins University Applied Physics Laboratory",
            "Leidos", "Lockheed Martin Corporation", "SRI International",
            "the Massachusetts Institute of Technology"]
        assert "unlinked: Booz Allen Hamilton" in check["note"]

    def test_a_recipient_list_whose_names_are_all_linked_passes(self, gate_fixture, tmp_path):
        from govbudget.export_site import fact_id_derived

        fid = fact_id_derived("concentration", PE, "program_dollars")
        self._cite(gate_fixture, {fid: {"kind": "derived", "units": "USD",
                                        "recorded_value": "74376328.830"}})
        self._set_players(gate_fixture, PE, [{
            "text": "Recorded recipients of awards linked to the program include"
                    " Raytheon Company and Northrop Grumman Systems Corp.",
            "citation": {"fact_id": fid}}])
        db = self._conc_duckdb(tmp_path, "GENERAL DYNAMICS", 4831.486, links=[
            ("RAYTHEON COMPANY", "UEI-RAY", "RAYTHEON"),
            ("NORTHROP GRUMMAN SYSTEMS CORP", "UEI-NG", "NORTHROP GRUMMAN"),
        ])
        res = _run_gate(gate_fixture, duckdb_path=db)
        assert res["checks"]["claims_agree_with_citations"]["ok"], res["checks"]

    def test_a_workbook_claim_contradicting_its_cell_fails(self, gate_fixture):
        self._cite(gate_fixture, {"wbcell": {
            "kind": "workbook", "units": "USD thousands", "amount_thousands": 897631.0,
            "amount_text": None, "recorded_value": None}})
        self._set_players(gate_fixture, PE, [{
            "text": "The FY 2026 request includes $273.379 million of discretionary"
                    " funding and $2,054.991 million of mandatory (reconciliation)"
                    " funding, for a total of $2,328.370 billion.",
            "citation": {"fact_id": "wbcell"}}])
        check = _run_gate(gate_fixture)["checks"]["claims_agree_with_citations"]
        assert not check["ok"]
        [bad] = check["contradictions"]
        assert bad["kind"] == "workbook" and bad["cited_value"] == 897631.0
        assert bad["reasons"] == ["stated_figure"]

    # -- disclosure: the note's reasons, read back ---------------------------

    @staticmethod
    def _emptied(gate_fixture, dropped: int, reasons: dict | None, pe=PE2):
        path = gate_fixture.dossier_dir / f"{pe}.json"
        doc = json.loads(path.read_text())
        doc["dossier"]["players"]["claims"] = []
        doc["dropped_claims"] = dropped
        doc["dropped_claims_by_section"] = {"players": dropped}
        if reasons is not None:
            doc["dropped_reasons"] = reasons
        path.write_text(json.dumps(doc))

    @staticmethod
    def _page(site_fixture, attr: int, text: str, page=PE2):
        built = site_fixture.tmp / "out"
        (built / "program" / page).mkdir(parents=True, exist_ok=True)
        (built / "program" / page / "index.html").write_text(
            '<html><body><div data-note-kind="scope"><p class="t-label mb-1">Correction</p>'
            f'<p class="text-sm leading-relaxed" data-dossier-dropped-claims="{attr}">'
            f"{text}</p></div></body></html>")
        return built

    def test_a_note_stating_the_wrong_reason_does_not_disclose(self, gate_fixture, site_fixture):
        self._emptied(gate_fixture, 2, {"contradicts_citation": 2})
        built = self._page(site_fixture, 2, "2 claims removed: they cited sources the site"
                                            " could not resolve.")
        req = _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]
        assert not req["ok"] and f"{PE2}: players" in req["empty"]
        assert any("stated figures, years or recipients their sources do not support" in u
                   for u in req["undisclosed"])

    def test_a_note_with_the_wrong_count_does_not_disclose(self, gate_fixture, site_fixture):
        self._emptied(gate_fixture, 2, {"contradicts_citation": 2})
        built = self._page(site_fixture, 3, "2 claims removed: they stated figures, years or"
                                            " recipients their sources do not support.")
        req = _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]
        assert not req["ok"]

    def test_the_true_note_discloses(self, gate_fixture, site_fixture):
        self._emptied(gate_fixture, 1, {"contradicts_citation": 1})
        built = self._page(site_fixture, 1, "1<!-- --> claim<!-- --> removed:<!-- --> <!-- -->"
                                            "it stated a figure, year or recipient its sources do not"
                                            " support<!-- -->.")
        res = _run_gate(gate_fixture, built_site_dir=built)
        assert res["checks"]["required_sections"]["ok"], res["checks"]["required_sections"]

    def test_every_reason_must_be_stated_with_its_own_count(self, gate_fixture, site_fixture):
        # the 0602025E shape after round 2: 4 lobbying drops + 4 withheld
        self._emptied(gate_fixture, 8, {"unresolvable_citation": 4, "contradicts_citation": 4})
        half = "8 claims removed: 4 cited sources the site could not resolve."
        built = self._page(site_fixture, 8, half)
        assert not _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]["ok"]
        full = ("8 claims removed: 4 cited sources the site could not resolve; 4 stated"
                " figures, years or recipients their sources do not support.")
        built = self._page(site_fixture, 8, full)
        assert _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]["ok"]

    def test_an_unknown_reason_cannot_be_disclosed(self, gate_fixture, site_fixture):
        self._emptied(gate_fixture, 1, {"some_future_reason": 1})
        built = self._page(site_fixture, 1, "1 claim removed: it did not meet the evidence"
                                            " standard.")
        req = _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]
        assert not req["ok"]

    def test_the_disclosure_is_read_on_the_member_page_not_the_bare_code(
        self, gate_fixture, site_fixture,
    ):
        """A split code's dossier renders on its member page (/program/3010-SCN/);
        the bare /program/3010/ is a disambiguation stub that never carries it."""
        slug = f"{PE2}-SCN"
        src = gate_fixture.dossier_dir / f"{PE2}.json"
        (gate_fixture.dossier_dir / f"{slug}.json").write_text(src.read_text())
        src.unlink()
        self._emptied(gate_fixture, 1, {"contradicts_citation": 1}, pe=slug)
        note = "1 claim removed: it stated a figure, year or recipient its sources do not support."
        built = self._page(site_fixture, 1, note, page=PE2)   # the stub: wrong page
        assert not _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]["ok"]
        built = self._page(site_fixture, 1, note, page=slug)
        assert _run_gate(gate_fixture, built_site_dir=built)["checks"]["required_sections"]["ok"]


class TestCorrectionNoteMirror:
    """gate.CORRECTION_CLAUSES mirrors program-dossier.tsx's Correction note
    word for word — the disclosure check compares the rendered sentence with
    the one these clauses build, so a wording change on either side must
    reach the other."""

    TSX = (Path(__file__).resolve().parents[1] / "site" / "src" / "components"
           / "program-dossier.tsx")

    def test_every_clause_is_in_the_component(self):
        from govbudget.dossiers.gate import CORRECTION_CLAUSES, CORRECTION_OTHER_CLAUSE

        src = self.TSX.read_text(encoding="utf-8")
        # the component's CORRECTION_CLAUSES table: reason: [one, many]
        for reason, (one, many) in CORRECTION_CLAUSES.items():
            entry = re.search(
                rf"\b{reason}:\s*\[\s*\"([^\"]+)\",\s*\"([^\"]+)\",?\s*\]", src)
            assert entry, reason
            assert (entry.group(1), entry.group(2)) == (one, many), reason
        assert f'OTHER_CLAUSE = "{CORRECTION_OTHER_CLAUSE}"' in src
        # and in the same order the gate builds the sentence in
        order = [src.index(f"{reason}:") for reason in CORRECTION_CLAUSES]
        assert order == sorted(order)

    @pytest.mark.parametrize("dropped,reasons,expected", [
        (3, None, "3 claims removed: they cited sources the site could not resolve."),
        (1, {"contradicts_citation": 1}, "1 claim removed: it stated a figure, year or recipient"
                                         " its sources do not support."),
        (4, {"unresolvable_citation": 1, "contradicts_citation": 3},
         "4 claims removed: one cited a source the site could not resolve; 3 stated"
         " figures, years or recipients their sources do not support."),
        (7, {"unresolvable_citation": 6, "stale_value": 1},
         "7 claims removed: 6 cited sources the site could not resolve; one stated a"
         " figure a later correction changed."),
        (2, {}, "2 claims removed: they did not meet the evidence standard."),
        (1, {"mystery": 1}, None),
    ])
    def test_the_expected_sentence(self, dropped, reasons, expected):
        from govbudget.dossiers.gate import expected_correction_note

        assert expected_correction_note(dropped, reasons) == expected


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERDRIFT round 3 (2026-09-26): fiscal-year label agreement. The
# gate reads each cited fact's column (scenario for a J-book glyph,
# amount_type for a workbook cell) from citations.parquet — citations.json
# does not carry them — and fails a published claim that names a year its
# cited column is not (/program/1203154SF/ what_it_is[3]: "For FY2026 …
# about $243.3 million (its Current Year amount)" on an FY 2025 glyph).
# ---------------------------------------------------------------------------

_FY_1203154SF = (
    "For FY2026, the Auxiliary Payloads project is funded at about $243.3"
    " million (its Current Year amount), making it the dominant project within"
    " the program."
)


class TestGateFiscalYear:
    _cite = staticmethod(TestGateClaimsAgreeWithCitations._cite)
    _set_players = staticmethod(TestGateClaimsAgreeWithCitations._set_players)

    @staticmethod
    def _parquet(path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        values = ", ".join(
            "(" + ", ".join("null" if v is None else f"'{v}'" for v in r) + ")" for r in rows)
        con.execute(f"copy (select * from (values {values}) t(fact_id, kind, scenario,"
                    f" amount_type)) to '{path}' (format parquet)")
        con.close()
        return path

    def _setup(self, fx, text=_FY_1203154SF):
        self._cite(fx, {"ef8d1da3e605d4f0": {
            "kind": "jbook_pdf", "units": "USD millions", "amount_text": "243.282",
            "amount_thousands": None, "recorded_value": None}})
        self._set_players(fx, PE, [{"text": text,
                                    "citation": {"fact_id": "ef8d1da3e605d4f0"}}])

    def test_the_parquet_beside_citations_json_is_read_and_the_claim_fails(self, gate_fixture):
        self._setup(gate_fixture)
        # the export's layout: json/citations.json beside citations/citations.parquet
        self._parquet(gate_fixture.citations.parent.parent / "citations" / "citations.parquet",
                      [("ef8d1da3e605d4f0", "jbook_pdf", "CurrentYear", None)])
        check = _run_gate(gate_fixture)["checks"]["claims_agree_with_citations"]
        assert not check["ok"] and check["fiscal_year_check"] is True
        [bad] = check["contradictions"]
        assert bad["reasons"] == ["fiscal_year"] and bad["fact_id"] == "ef8d1da3e605d4f0"

    def test_a_correctly_labelled_claim_passes(self, gate_fixture, tmp_path):
        self._setup(gate_fixture, _FY_1203154SF.replace("FY2026", "FY2025"))
        pq = self._parquet(tmp_path / "c.parquet",
                           [("ef8d1da3e605d4f0", "jbook_pdf", "CurrentYear", None)])
        check = _run_gate(gate_fixture, citations_parquet=pq)["checks"][
            "claims_agree_with_citations"]
        assert check["ok"] and check["fiscal_year_check"] is True

    def test_without_the_parquet_the_leg_says_it_did_not_run(self, gate_fixture):
        self._setup(gate_fixture)
        check = _run_gate(gate_fixture)["checks"]["claims_agree_with_citations"]
        assert check["ok"] and check["fiscal_year_check"] is False
        assert "fiscal-year leg not run" in check["note"]

    def test_an_unreadable_parquet_fails_closed(self, gate_fixture, tmp_path):
        self._setup(gate_fixture)
        check = _run_gate(gate_fixture, citations_parquet=tmp_path / "absent.parquet")[
            "checks"]["claims_agree_with_citations"]
        assert not check["ok"] and check["error"] and check["fiscal_year_check"] is False
