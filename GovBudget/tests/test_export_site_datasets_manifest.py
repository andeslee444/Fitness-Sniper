"""Explorer dataset manifest — PM-review Sprint 2, spec §P1-5.

The /data/ page used to hardcode row counts and hand-written descriptions in
TSX; eight of them had rotted to 5B-2-era values (dim_programs said 326 while
the parquet held 1,739) and budget_lines_decade had no card at all. These tests
pin the replacement: a build-emitted manifest whose counts come from the
written parquets and whose scope sentences cannot be silently omitted.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from govbudget.export_site import _DATASET_SCOPES, _build_dataset_manifest


def _touch_parquets(tmp_path, names, sizes=None):
    """Create fake parquet files (byte size is all _build_dataset_manifest reads)."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(names):
        size = (sizes or {}).get(n, 10 + i)
        (data_dir / f"{n}.parquet").write_bytes(b"x" * size)
    return data_dir


class TestDatasetScopes:
    def test_every_scope_is_a_real_grain_sentence(self):
        assert _DATASET_SCOPES, "scope table must not be empty"
        for name, scope in _DATASET_SCOPES.items():
            assert isinstance(scope, str)
            # A grain sentence, not a label: says what ONE row is, ends in a
            # full stop, and is long enough to actually scope the dataset.
            assert len(scope) >= 60, f"{name}: scope too short to be a grain sentence"
            assert scope.rstrip().endswith("."), f"{name}: scope must be a sentence"
            assert "row" in scope.lower(), f"{name}: scope must describe the row grain"

    def test_scope_table_covers_the_datasets_the_site_ships(self):
        """The 15 Explorer parquets the exporter writes are all documented."""
        expected = {
            "budget_lines",
            "budget_lines_decade",
            "dim_entities",
            "dim_geography",
            "dim_lobbyists",
            "dim_programs",
            "fct_budget_to_awards",
            "fct_budget_trajectory",
            "fct_improper_exposure",
            "fct_influence",
            "fct_program_concentration",
            "fct_program_lobbying",
            "fct_state_per_capita",
            "jbook_details",
            "jbook_narratives",
        }
        assert expected <= set(_DATASET_SCOPES), (
            "undocumented dataset(s): " + ", ".join(sorted(expected - set(_DATASET_SCOPES)))
        )

    def test_dim_programs_scope_disowns_the_full_page_universe(self):
        """§P1-5 root cause: users read 'dim_programs' as 'all our programs'."""
        scope = _DATASET_SCOPES["dim_programs"].lower()
        assert "detail" in scope
        assert "not the full page universe" in scope

    def test_decade_scope_states_the_edition_grain(self):
        scope = _DATASET_SCOPES["budget_lines_decade"].lower()
        assert "edition" in scope
        assert "pb2017" in scope and "pb2026" in scope

    def test_dim_entities_scope_states_the_sam_shape_not_a_state(self):
        """ROADMAP #10: the sam_* columns fill over ~20 days of a 10/day key.

        "NULL in every row until that extract runs" is a hand-typed claim
        about WHEN, and it is false for every day of that partial run — the
        one window in which a reader is most likely to meet a half-filled
        column and check the card. The shape ("where it has reached … NULL
        wherever it has not") is true before, during and after, and the count
        itself lives in site_meta.counts.companies_with_sam.
        """
        scope = _DATASET_SCOPES["dim_entities"].lower()
        assert "where the bounded extract has reached it" in scope
        assert "null wherever it has not" in scope
        assert "null in every row" not in scope


class TestBuildDatasetManifest:
    def test_counts_and_sizes_come_from_the_build_not_a_literal(self, tmp_path):
        data_dir = _touch_parquets(
            tmp_path, ["dim_programs", "budget_lines"], sizes={"dim_programs": 77}
        )
        m = _build_dataset_manifest(
            data_dir,
            row_counts={"dim_programs": 1739, "budget_lines": 8549},
            uncited=[],
            built_at="2026-08-03T00:00:00+00:00",
        )
        by_name = {d["name"]: d for d in m["datasets"]}
        assert by_name["dim_programs"]["row_count"] == 1739
        assert by_name["dim_programs"]["bytes"] == 77
        assert by_name["dim_programs"]["file"] == "dim_programs.parquet"
        assert by_name["budget_lines"]["row_count"] == 8549
        assert m["schema_version"] == 1
        assert m["built_at"] == "2026-08-03T00:00:00+00:00"

    def test_every_shipped_parquet_gets_an_entry(self, tmp_path):
        names = sorted(_DATASET_SCOPES)
        data_dir = _touch_parquets(tmp_path, names)
        m = _build_dataset_manifest(
            data_dir,
            row_counts={n: 1 for n in names},
            uncited=[],
            built_at="x",
        )
        assert {d["name"] for d in m["datasets"]} == set(names)

    def test_undocumented_parquet_fails_the_export(self, tmp_path):
        """A new mart cannot ship without a scope sentence."""
        data_dir = _touch_parquets(tmp_path, ["dim_programs", "fct_brand_new_mart"])
        with pytest.raises(ValueError, match="fct_brand_new_mart"):
            _build_dataset_manifest(
                data_dir,
                row_counts={"dim_programs": 1, "fct_brand_new_mart": 2},
                uncited=[],
                built_at="x",
            )

    def test_cited_flag_tracks_the_uncited_ledger(self, tmp_path):
        data_dir = _touch_parquets(tmp_path, ["dim_programs", "dim_lobbyists"])
        m = _build_dataset_manifest(
            data_dir,
            row_counts={"dim_programs": 1, "dim_lobbyists": 2},
            uncited=["dim_lobbyists"],
            built_at="x",
        )
        by_name = {d["name"]: d for d in m["datasets"]}
        assert by_name["dim_programs"]["cited"] is True
        assert by_name["dim_lobbyists"]["cited"] is False

    def test_presentation_order_is_the_scope_table_order(self, tmp_path):
        names = ["dim_programs", "budget_lines", "jbook_details"]
        data_dir = _touch_parquets(tmp_path, names)
        m = _build_dataset_manifest(
            data_dir, row_counts={n: 1 for n in names}, uncited=[], built_at="x"
        )
        expected = [n for n in _DATASET_SCOPES if n in names]
        assert [d["name"] for d in m["datasets"]] == expected

    def test_missing_row_count_degrades_to_zero_not_a_crash(self, tmp_path):
        data_dir = _touch_parquets(tmp_path, ["dim_programs"])
        m = _build_dataset_manifest(
            data_dir, row_counts={}, uncited=[], built_at="x"
        )
        assert m["datasets"][0]["row_count"] == 0

    def test_manifest_is_json_serialisable(self, tmp_path):
        data_dir = _touch_parquets(tmp_path, ["dim_programs"])
        m = _build_dataset_manifest(
            data_dir, row_counts={"dim_programs": 1739}, uncited=[], built_at="x"
        )
        json.dumps(m)


class TestProgramConcentrationScopeMirrorsTheMart:
    """The /data/ scope sentence and the dbt description are ONE statement.

    #80 fix round 3 (2026-09-11, finding 2): the floor sentence for
    fct_program_concentration drifted from the mart twice in two review
    rounds — first stating two of the mart's three floor clauses, then
    opening with a dollar gate the mart does not apply — and both fixes
    landed as prose with nothing behind them. These bind the two mirrors:
    every floor clause is asserted in BOTH the exporter's scope sentence
    (rendered verbatim on /data/ and /downloads/) and the
    fct_program_concentration description in dbt/models/marts/schema.yml, so
    editing one alone fails here.

    The mart itself is the third mirror, guarded on the Python side by
    verify_phase3's marts_gate floor leg (#80 fix round 1).
    """

    SCHEMA_YML = (
        Path(__file__).resolve().parents[1]
        / "dbt" / "models" / "marts" / "schema.yml"
    )

    # Phrases that must appear in BOTH surfaces, whitespace-normalized and
    # case-folded. Each names one of the mart's three floor clauses
    # (fct_program_concentration.sql:156-167) or the column that makes the
    # second clause auditable from the download alone.
    SHARED_FLOOR_CLAUSES = (
        "hhi_high and top_family_high are null below the floor",
        "3 linked awards",
        "2 families holding positive dollars (positive_family_count_high)",
    )

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    @classmethod
    def _schema_description(cls) -> str:
        doc = yaml.safe_load(cls.SCHEMA_YML.read_text(encoding="utf-8"))
        models = {m["name"]: m for m in doc["models"]}
        assert "fct_program_concentration" in models, (
            "dbt/models/marts/schema.yml no longer documents "
            "fct_program_concentration — the /data/ mirror lost its source"
        )
        return models["fct_program_concentration"]["description"]

    def test_both_mirrors_state_all_three_floor_clauses(self):
        scope = self._norm(_DATASET_SCOPES["fct_program_concentration"])
        schema = self._norm(self._schema_description())
        for clause in self.SHARED_FLOOR_CLAUSES:
            assert clause in scope, f"/data/ scope dropped: {clause}"
            assert clause in schema, f"schema.yml description dropped: {clause}"
        # The third clause is worded "positive net program_dollars_high" in
        # the warehouse and "positive program_dollars_high" on /data/.
        for name, text in (("/data/ scope", scope), ("schema.yml", schema)):
            assert re.search(r"positive (net )?program_dollars_high", text), (
                f"{name} dropped the positive-net-dollars clause"
            )
            # Both bases ship in the download and both are named.
            assert "two bases" in text, f"{name} dropped the two-basis grain"
            assert "*_all over every published link" in text, name
            assert "*_high over high-confidence links" in text, name

    def test_the_scope_opens_with_the_grain_not_a_dollar_gate(self):
        """#80 fix round 3, finding 1: the mart applies NO dollar gate.

        Its row set is every pe_bli in fct_budget_to_awards — 444 rows, 64 of
        them with program_dollars_all <= 0 and 59 with hhi_all = 0.0 (the
        `else 0` share branch, not a concentration score). A downloader
        reading the old opening clause concluded all 444 carry a meaningful
        index.
        """
        scope = self._norm(_DATASET_SCOPES["fct_program_concentration"])
        assert scope.startswith(
            "one row per program element carrying at least one published"
            " crosswalk link,"
        ), _DATASET_SCOPES["fct_program_concentration"]
        opening = scope.split("on two bases")[0]
        assert "dollars" not in opening, (
            "the row set is not dollar-gated; say the grain: " + opening
        )
