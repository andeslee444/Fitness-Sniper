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


#: Datasets whose /downloads/ caveat is MEASURED from the file, so the file
#: must be a real parquet: fct_program_concentration's caveat (ROADMAP #130)
#: raises on an unreadable file rather than dropping its sentence.
_READ_BY_CAVEAT = {"fct_program_concentration"}


def _touch_parquets(tmp_path, names, sizes=None):
    """Create fake parquet files (byte size is all _build_dataset_manifest
    reads — except for the datasets in _READ_BY_CAVEAT, which get a real,
    scope-less one-row parquet)."""
    import duckdb

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(names):
        if n in _READ_BY_CAVEAT:
            con = duckdb.connect()
            try:
                con.execute(f"copy (select 1 as pe_bli) to '{data_dir / n}.parquet'"
                            " (format parquet)")
            finally:
                con.close()
            continue
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


# ---------------------------------------------------------------------------
# ROADMAP #130 (owner-delegated ruling 2026-09-25): the downloadable
# warehouse LABELS a shared code's pooled concentration row instead of
# withholding it. The export copies fct_program_concentration wholesale
# (`select *`), so the dbt lane's scope columns ship; the /downloads/ card
# must say what those rows are, measured from the shipped file.
# ---------------------------------------------------------------------------


def _concentration_parquet(tmp_path, rows, *, with_scope=True):
    import duckdb

    pq = tmp_path / "fct_program_concentration.parquet"
    con = duckdb.connect()
    try:
        cols = "pe_bli varchar, hhi_all double"
        if with_scope:
            cols += (", scope varchar, member_programs integer,"
                     " member_keys_with_links integer,"
                     " links_outside_member_keys integer")
        con.execute(f"create table t ({cols})")
        for r in rows:
            ph = ",".join("?" for _ in r)
            con.execute(f"insert into t values ({ph})", r)
        con.execute(f"copy t to '{pq}' (format parquet)")
    finally:
        con.close()
    return pq


#: The member page `_concentration_page` hands each single-member code to
#: (R-DEC-130c): 2101/2292/3050/4217 on the measured lake (2026-09-25).
_OWNERS = {
    "2101": ("2101-WPN", "Tactical Tomahawk"),
    "2292": ("2292-WPN", "Naval Strike Missile (NSM)"),
    "3050": ("3050-OPN", "Standard Missile"),
    "4217": ("4217-OPN", "Ship Gun System"),
}


def _owner_page(pe_bli):
    """A stand-in for export_site._concentration_page: the member page a
    code-level figure belongs to, or None when it belongs to no one member."""
    return _OWNERS.get(pe_bli)


def test_concentration_caveat_counts_the_code_level_rows(tmp_path):
    from govbudget.export_site import _derived_caveat

    pq = _concentration_parquet(tmp_path, [
        ("0601101E", 1200.0, "program", 1, 1, 0),
        ("3010", 9329.0, "code", 2, 2, 0),
        ("3215", 5000.0, "code", 2, 2, 0),
    ])
    caveat = _derived_caveat("fct_program_concentration", pq,
                             concentration_page=_owner_page)
    assert caveat.startswith("2 of its 3 rows are code-level")
    assert "scope = 'code'" in caveat
    assert "pools every member key with links" in caveat
    assert "member_keys_with_links" in caveat


def test_the_caveat_is_per_row_pooled_versus_one_members_figure(tmp_path):
    """R-DEC-130c: "pools every member key with links" only where
    member_keys_with_links > 1 (0145, 3010, 3215); a code on which ONE member
    carries every link (2101, 2292, 3050, 4217) says whose figure it is —
    the member _concentration_owner hands it to, as the program pages do.
    The stage-1 sentence said every code-level row "describes no single
    program", false for 4 of the 7."""
    from govbudget.export_site import _derived_caveat

    pq = _concentration_parquet(tmp_path, [
        ("0601101E", 1200.0, "program", 1, 1, 0),
        ("0145", 3500.0, "code", 2, 2, 0),
        ("2101", 10000.0, "code", 2, 1, 0),
        ("2292", 10000.0, "code", 2, 1, 0),
        ("3010", 9329.0, "code", 2, 2, 0),
        ("3050", 4373.59, "code", 2, 1, 0),
        ("3215", 5000.0, "code", 2, 2, 0),
        ("4217", 10000.0, "code", 2, 1, 0),
    ])
    caveat = _derived_caveat("fct_program_concentration", pq,
                             concentration_page=_owner_page)
    assert caveat.startswith("7 of its 8 rows are code-level")
    pooled, _, single = caveat.partition("pools every member key with links")
    assert "On 3 of them (0145, 3010 and 3215)" in pooled
    for code in ("2101", "2292", "3050", "4217"):
        assert code not in pooled, f"{code} is one member's figure, not pooled"
    assert "On 4 (2101, 2292, 3050 and 4217) one member's key carries every link" in caveat
    for code, (slug, _title) in _OWNERS.items():
        assert f"{code} is {slug}'s" in single
    # "describes no single program" is said of the pooled rows only.
    assert caveat.count("describes no single program") == 1
    assert caveat.index("describes no single program") < caveat.index("2101 is")


def test_a_code_with_links_under_no_members_key_is_no_ones_figure(tmp_path):
    """One member carries links AND some sit under no member's key
    (links_outside_member_keys > 0): _concentration_owner hands the figure to
    no one, and the caveat says why — it neither names a member nor calls
    the row pooled over member keys."""
    from govbudget.export_site import _derived_caveat

    pq = _concentration_parquet(tmp_path, [
        ("5555", 100.0, "code", 2, 1, 3),
        ("3010", 9329.0, "code", 2, 2, 0),
    ])
    caveat = _derived_caveat("fct_program_concentration", pq,
                             concentration_page=lambda _pe: None)
    assert "On 1 (5555) some links sit under no member's key" in caveat
    assert "links_outside_member_keys" in caveat
    assert "5555 is" not in caveat


def test_the_caveat_refuses_to_disagree_with_the_program_pages(tmp_path):
    """The mart's member_keys_with_links and _concentration_owner are two
    computations of one rule; a disagreement is refused, never papered over
    (the stage-1 sentence contradicted four program pages)."""
    from govbudget.export_site import _derived_caveat

    one_member = _concentration_parquet(tmp_path, [("2101", 1.0, "code", 2, 1, 0)])
    with pytest.raises(ValueError, match="2101"):
        _derived_caveat("fct_program_concentration", one_member,
                        concentration_page=lambda _pe: None)
    (tmp_path / "fct_program_concentration.parquet").unlink()
    pooled = _concentration_parquet(tmp_path, [("3010", 1.0, "code", 2, 2, 0)])
    with pytest.raises(ValueError, match="3010"):
        _derived_caveat("fct_program_concentration", pooled,
                        concentration_page=lambda _pe: ("3010-SCN", "t"))


def test_a_single_member_row_cannot_be_named_without_the_owner_rule(tmp_path):
    from govbudget.export_site import _derived_caveat

    pq = _concentration_parquet(tmp_path, [("2101", 1.0, "code", 2, 1, 0)])
    with pytest.raises(ValueError, match="concentration_page"):
        _derived_caveat("fct_program_concentration", pq)


def test_the_manifest_threads_the_owner_rule_to_the_caveat(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _concentration_parquet(data_dir, [
        ("2101", 10000.0, "code", 2, 1, 0),
        ("3010", 9329.0, "code", 2, 2, 0),
    ])
    m = _build_dataset_manifest(
        data_dir, row_counts={"fct_program_concentration": 2}, uncited=[],
        built_at="2026-09-26T00:00:00Z", concentration_page=_owner_page)
    (entry,) = m["datasets"]
    assert "2101 is 2101-WPN's" in entry["caveat"]


def test_the_export_resolves_owners_with_the_program_pages_rule():
    """The resolver the export hands the manifest is _concentration_page over
    the export's own identity map, links and member pages."""
    from govbudget.export_site import (
        _ProgramIdentity,
        _concentration_page_resolver,
        _member_pages,
    )

    rows = [("2101", "1507N", "Weapons Procurement, Navy", "N"),
            ("2101", "1810N", "Other Procurement, Navy", "N"),
            ("0145", "1506N", "Aircraft Procurement, Navy", "N"),
            ("0145", "1508N", "Procurement of Ammunition, Navy and Marine Corps", "N")]
    ident = _ProgramIdentity([r + (True,) for r in rows])
    pages = _member_pages(ident, [r + ("T",) for r in rows])
    links = {ident.split_key("2101", "1507N", "N"): ["A"],
             ident.split_key("0145", "1506N", "N"): ["B"],
             ident.split_key("0145", "1508N", "N"): ["C"]}
    resolve = _concentration_page_resolver(ident, links, pages)
    assert resolve("2101") == ("2101-WPN", "T")
    assert resolve("0145") is None


def test_concentration_caveat_is_absent_before_the_scope_column_exists(tmp_path):
    from govbudget.export_site import _derived_caveat

    pq = _concentration_parquet(tmp_path, [("3010", 9329.0)], with_scope=False)
    assert _derived_caveat("fct_program_concentration", pq) == ""


def test_concentration_caveat_says_nothing_when_no_code_is_shared(tmp_path):
    from govbudget.export_site import _derived_caveat

    pq = _concentration_parquet(tmp_path, [("0601101E", 1.0, "program", 1, 1, 0)])
    assert _derived_caveat("fct_program_concentration", pq) == ""


def test_the_caveat_names_only_columns_the_mart_documents():
    """Pairing with dbt/models/marts/schema.yml: the caveat names the scope
    columns by name, so they must be the ones the mart documents."""
    from govbudget.export_site import (
        _CONCENTRATION_CODE_SCOPE,
        _CONCENTRATION_MEMBER_KEYS_COLUMN,
        _CONCENTRATION_OUTSIDE_KEYS_COLUMN,
        _CONCENTRATION_SCOPE_COLUMN,
    )

    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "dbt" / "models" / "marts"
         / "schema.yml").read_text())
    model = next(m for m in schema["models"]
                 if m["name"] == "fct_program_concentration")
    cols = {c["name"]: c for c in model.get("columns", [])}
    assert _CONCENTRATION_SCOPE_COLUMN in cols
    assert _CONCENTRATION_MEMBER_KEYS_COLUMN in cols
    assert _CONCENTRATION_OUTSIDE_KEYS_COLUMN in cols
    # The value the caveat counts is the one the column documents for a
    # shared code (the values are asserted by a singular dbt test, so the
    # description is where schema.yml names them).
    assert (f"'{_CONCENTRATION_CODE_SCOPE}'"
            in cols[_CONCENTRATION_SCOPE_COLUMN].get("description", ""))
