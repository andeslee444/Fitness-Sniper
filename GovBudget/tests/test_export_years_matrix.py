"""Tests for Phase 5D Task 1: years_matrix.json + sharded citation slices.

TDD scope (plan 2026-07-02-phase5d-years-matrix Task 1, tests a-h):
  (a) matrix sidecar exists with org→programs→projects nesting
  (b) a known program's FY24 cell equals the fct_budget_lines detail-row value
      with its workbook fact_id (incl. the CYBERCOM→CYBER org translation)
  (c) a known project cell equals its jbook_details row + jbook_pdf fact_id
  (d) Δ cells carry trajectory derived fact_ids; multi-line pivot cells fall
      back to the derived trajectory fact_id (the cited sum)
  (e) missing values are null/absent, never 0; multi-line cells for
      amount_types with NO derived citation are absent (no uncited sums)
  (f) every fid in the matrix exists in exactly the right shard file
  (g) shard union == citations_dict keys (no orphans, no misses), shard rows
      byte-identical to the citations.json values
  (h) payload < 900 KB raw (loud exporter guard + live-file check)

Cell contract (BINDING for the /years/ page and the G8 yearsmatrix gate):
  program cells keyed by amount_type; each cell {"v": float, "fid": str|null}.
  - exactly one cited budget_lines detail row → v = amount_thousands,
    fid = the workbook fact_id (the direct receipt)
  - zero or >1 detail rows for a trajectory-covered amount_type → v = the
    fct_budget_trajectory value, fid = the derived trajectory fact_id
    (the recompute-verified cited sum)
  - otherwise the cell is ABSENT (missing → "–", never 0, never uncited sums)
  Δ cell key 'fy2526_change' (derived fid); '%Δ' key 'fy2526_pct_change'
  carries {"v": pct} with NO fid (mart-computed presentation figure, only
  emitted when the cited Δ cell is present).
  project cells keyed fy2024/fy2025/fy2026 (PriorYear/CurrentYear/
  BudgetYearOne); cited rows carry fid, uncited zero_amount rows carry
  xp (xml_path, Cite state B).
"""
from __future__ import annotations

import gzip
import hashlib
import inspect
import json
from pathlib import Path

import duckdb
import pytest

import govbudget.export_site as es
from govbudget.config import ROOT as _ROOT
from govbudget.export_site import (
    _emit_cite_shards,
    _emit_years_matrix,
    fact_id_derived,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

# Workbook fact_ids (16-hex-ish literals are fine — the emitters treat them
# as opaque strings; shard tests need real [0:2] prefixes)
W_DARPA_24 = "aa11000000000001"
W_DARPA_25A = "aa11000000000002"
W_DARPA_25B = "ab11000000000003"
W_DARPA_26 = "ac11000000000004"
W_DARPA_25E_A = "ad11000000000005"
W_DARPA_25E_B = "ae11000000000006"
W_ARMY_24 = "ba11000000000007"
W_CYBER_24 = "ca11000000000008"
J_P1_PRIOR = "da11000000000009"
J_P1_BY1 = "db1100000000000a"

D_DARPA_25 = fact_id_derived("trajectory", "0601101E|DARPA", "fy2025_total")
D_DARPA_CHG = fact_id_derived("trajectory", "0601101E|DARPA", "fy2526_change")
D_ARMY_CHG = fact_id_derived("trajectory", "0602303A|A", "fy2526_change")
D_CYBER_CHG = fact_id_derived("trajectory", "0303140K|CYBER", "fy2526_change")

# ---------------------------------------------------------------------------
# Phase 5E Task 6 decade fixtures — grains are
# (pe_bli, fy, edition_year, amount_type_kind, amount_thousands, fid,
#  amount_type) (7-tuple since PM Sprint 1: the trailing chosen slug feeds
# slug-accurate `measure` derivation in the sidecar/summary consumers)
# ---------------------------------------------------------------------------

W_DEC_20A = "ea11000000000010"   # single-source FY2020 actuals (PB2022)
W_DEC_25E = "eb11000000000011"   # single-source FY2025 enacted (PB2026)
UNCITED_DEC = "ec11000000000012"  # decade grain with NO citation row
D_DEC_15A = fact_id_derived("decade", "0601101E|2017", "fy_2015_actuals")


def _decade_grains() -> list[tuple]:
    """9-tuples since ROADMAP #45 (8-tuples since Sprint E, ROADMAP #67 /
    Task E3) — the trailing `account`/`organization` are both None for
    every row here; none of these fixture pe_blis is one of the 8 genuine
    appropriation-account collisions or the 3 organization collisions."""
    return [
        # FY2020 actuals from PB2022 (edition-authoritative rule: PB(N+2))
        ("0601101E", 2020, 2022, "actuals", 150000.0, W_DEC_20A,
         "fy_2020_actuals", None, None),
        # FY2015 actuals from PB2017 — multi-source grain → derived decade fid
        ("0601101E", 2015, 2017, "actuals", 90000.0, D_DEC_15A,
         "fy_2015_actuals", None, None),
        # FY2025 enacted from PB2026 CurrentYear
        ("0601101E", 2025, 2026, "enacted", 200000.0, W_DEC_25E,
         "fy_2025_enacted", None, None),
        # FY2026 request from PB2026 BudgetYearOne — reuses the workbook fid
        ("0601101E", 2026, 2026, "request", 400000.0, W_DARPA_26,
         "fy_2026_total", None, None),
        # UNCITED grain — the cell must be honestly absent
        ("0303140K", 2020, 2022, "actuals", 30000.0, UNCITED_DEC,
         "fy_2020_actuals", None, None),
    ]


def _make_duckdb_with_trajectory(tmp_path: Path) -> Path:
    db_path = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE fct_budget_trajectory ("
        "  pe_bli varchar, organization varchar,"
        "  fy2024_actuals double, fy2025_total double, fy2026_total double,"
        "  fy2526_change double, fy2526_pct_change double"
        ")"
    )
    con.execute(
        "INSERT INTO fct_budget_trajectory VALUES "
        # DARPA: fy25 has TWO detail rows (120k + 80k) → pivot fallback
        "('0601101E', 'DARPA', 100000.0, 200000.0, 400000.0, 200000.0, 100.0),"
        # Army (workbook-code org, synth-style): zeroed FY26
        "('0602303A', 'A', 50000.0, 60000.0, 0.0, -60000.0, -100.0),"
        # CYBERCOM program: trajectory keyed by workbook org CYBER
        "('0303140K', 'CYBER', 30000.0, 35000.0, 40000.0, 5000.0, 14.29)"
    )
    con.close()
    return db_path


def _all_prog_rows() -> list[tuple]:
    """(pe_bli, org, exhibit_family, title, project_count, fy2024m,
    fully_reconciled, account, account_title) — the last two (Sprint E,
    ROADMAP #67 / Task E3) are None for every ordinary, non-split program;
    none of these three fixture rows is one of the 8 genuine
    appropriation-account collisions."""
    return [
        ("0601101E", "DARPA", "rdte", "DARPA Research", 1, 100.0, True, None, None),
        ("0602303A", "A", "rdte", "Army Research Lab", 0, None, False, None, None),
        ("0303140K", "CYBERCOM", "rdte", "Cyber Ops", 0, 30.0, False, None, None),
    ]


def _bl_row(fid, pe, org, amount_type, amount, title="Line"):
    """16-tuple matching the export pass bl_rows shape."""
    return (
        fid, "R-1", 2026, "2040", "RDT&E", org, "3", "Adv Tech",
        pe, title, amount_type, amount, "USD thousands",
        "sha_wb", "Exhibit R-1", "D5",
    )


def _bl_rows() -> list[tuple]:
    return [
        _bl_row(W_DARPA_24, "0601101E", "DARPA", "fy_2024_actuals", 100000.0),
        # TWO fy_2025_total rows → cell must fall back to the derived traj fid
        _bl_row(W_DARPA_25A, "0601101E", "DARPA", "fy_2025_total", 120000.0),
        _bl_row(W_DARPA_25B, "0601101E", "DARPA", "fy_2025_total", 80000.0),
        _bl_row(W_DARPA_26, "0601101E", "DARPA", "fy_2026_total", 400000.0),
        # TWO fy_2025_enacted rows — NO derived citation exists for this
        # amount_type → the cell must be ABSENT (never an uncited sum)
        _bl_row(W_DARPA_25E_A, "0601101E", "DARPA", "fy_2025_enacted", 90000.0),
        _bl_row(W_DARPA_25E_B, "0601101E", "DARPA", "fy_2025_enacted", 95000.0),
        _bl_row(W_ARMY_24, "0602303A", "A", "fy_2024_actuals", 50000.0),
        # CYBERCOM program's lines live under workbook org CYBER
        _bl_row(W_CYBER_24, "0303140K", "CYBER", "fy_2024_actuals", 30000.0),
    ]


def _detail_row(fid, pe, pn, pt, scenario, amount, xml_path, resolution,
                account=None):
    """14-tuple matching the export pass detail_rows shape.

    `account` (Wave 5, last position) is the detail row's own appropriation —
    NULL for R-2/RDT&E rows, which is what these DARPA fixtures are."""
    return (
        fid, pe, pn, pt, scenario, amount, "USD millions", xml_path,
        "DARPA", "rdte", 2026, "sha_jb", resolution, account,
    )


def _detail_rows() -> list[tuple]:
    return [
        # root row (project_number None) — never a project sub-row
        _detail_row("dc1100000000000b", "0601101E", None, None, "PriorYear",
                    100.0, "ProgramElement[1]", "unique"),
        _detail_row(J_P1_PRIOR, "0601101E", "P1", "Project One", "PriorYear",
                    12.5, "ProgramElement[1]/Project[0]", "unique"),
        # zero_amount project cell — uncited, carries xml_path (state B)
        _detail_row(J_P1_BY1, "0601101E", "P1", "Project One", "BudgetYearOne",
                    0.0, "ProgramElement[1]/Project[1]", "zero_amount"),
    ]


def _cited_fact_ids() -> set[str]:
    return {
        W_DARPA_24, W_DARPA_25A, W_DARPA_25B, W_DARPA_26,
        W_DARPA_25E_A, W_DARPA_25E_B, W_ARMY_24, W_CYBER_24,
        W_DEC_20A, W_DEC_25E, D_DEC_15A,  # decade fids (UNCITED_DEC absent)
        J_P1_PRIOR,  # J_P1_BY1 is zero_amount → NOT cited
        "dc1100000000000b",
        fact_id_derived("trajectory", "0601101E|DARPA", "fy2024_actuals"),
        D_DARPA_25,
        fact_id_derived("trajectory", "0601101E|DARPA", "fy2026_total"),
        D_DARPA_CHG,
        fact_id_derived("trajectory", "0602303A|A", "fy2024_actuals"),
        fact_id_derived("trajectory", "0602303A|A", "fy2025_total"),
        fact_id_derived("trajectory", "0602303A|A", "fy2026_total"),
        D_ARMY_CHG,
        fact_id_derived("trajectory", "0303140K|CYBER", "fy2024_actuals"),
        fact_id_derived("trajectory", "0303140K|CYBER", "fy2025_total"),
        fact_id_derived("trajectory", "0303140K|CYBER", "fy2026_total"),
        D_CYBER_CHG,
    }


def _emit(
    tmp_path: Path,
    decade_grains: list | None = None,
    *,
    extra_cited: frozenset[str] = frozenset(),
) -> dict:
    db_path = _make_duckdb_with_trajectory(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        payload = _emit_years_matrix(
            json_dir=json_dir,
            con=con,
            all_prog_rows=_all_prog_rows(),
            detail_rows=_detail_rows(),
            bl_rows=_bl_rows(),
            cited_fact_ids=_cited_fact_ids() | set(extra_cited),
            decade_grains=decade_grains,
        )
    finally:
        con.close()
    return payload


def _read_written(json_dir: Path) -> dict:
    """The three /years/ files as written, merged back into the v1 view."""
    core = json.loads((json_dir / "years_matrix.json").read_text())
    shards = [
        json.loads((json_dir / "years_matrix" / f"{name}.json").read_text())
        for name in ("decade", "detail")
    ]
    return es.merge_years_matrix(core, *shards)


def _strip_split_keys(view: dict) -> dict:
    """A payload or merged view without the keys the split adds (design
    §3.3: merge(split(p)) == p ignoring schema_version, build_id, shards
    and np)."""
    out = {k: v for k, v in view.items() if k not in ("schema_version", "build_id", "shards")}
    out["orgs"] = [
        {**o, "programs": [{k: v for k, v in p.items() if k != "np"} for p in o["programs"]]}
        for o in view["orgs"]
    ]
    return out


def _program(payload: dict, pe_bli: str) -> dict:
    for org in payload["orgs"]:
        for p in org["programs"]:
            if p["pe_bli"] == pe_bli:
                return p
    raise AssertionError(f"program {pe_bli} not in matrix")


# ---------------------------------------------------------------------------
# (a) structure
# ---------------------------------------------------------------------------


class TestMatrixStructure:
    def test_creates_years_matrix_json(self, tmp_path):
        payload = _emit(tmp_path)
        path = tmp_path / "json" / "years_matrix.json"
        assert path.exists(), "years_matrix.json was not created"
        # #193: the core plus two shards, which merge back into the payload
        assert _strip_split_keys(_read_written(tmp_path / "json")) == (
            _strip_split_keys(payload)
        )

    def test_top_level_contract(self, tmp_path):
        payload = _emit(tmp_path)
        for key in ("schema_version", "program_units", "project_units",
                    "amount_types", "delta_columns", "default_columns",
                    "project_scenarios", "orgs"):
            assert key in payload, f"missing top-level key {key!r}"
        assert payload["program_units"] == "USD thousands"
        assert payload["project_units"] == "USD millions"
        assert payload["delta_columns"] == ["fy2526_change", "fy2526_pct_change"]
        assert payload["project_scenarios"] == {
            "fy2024": "PriorYear",
            "fy2025": "CurrentYear",
            "fy2026": "BudgetYearOne",
        }

    def test_org_sections_sorted_and_programs_grouped(self, tmp_path):
        payload = _emit(tmp_path)
        orgs = [o["org"] for o in payload["orgs"]]
        assert orgs == sorted(orgs)
        assert set(orgs) == {"DARPA", "A", "CYBERCOM"}
        darpa = next(o for o in payload["orgs"] if o["org"] == "DARPA")
        assert [p["pe_bli"] for p in darpa["programs"]] == ["0601101E"]
        prog = darpa["programs"][0]
        assert prog["title"] == "DARPA Research"
        assert isinstance(prog["cells"], dict)
        assert isinstance(prog["projects"], list)

    def test_amount_types_present_in_canonical_order(self, tmp_path):
        """Only amount_types with ≥1 EMITTED cell appear — fy_2025_enacted's
        sole rows are the multi-line uncitable DARPA pair (absent cell), so
        the column is dropped rather than shipped as a dead all-'–' column."""
        payload = _emit(tmp_path)
        assert payload["amount_types"] == [
            "fy_2024_actuals", "fy_2025_total", "fy_2026_total",
        ]

    def test_amount_type_outside_program_set_dropped(self, tmp_path):
        """A workbook amount_type whose only rows belong to pe_blis outside
        the program set (e.g. fy_2025_supplemental live) never becomes a
        column."""
        db_path = _make_duckdb_with_trajectory(tmp_path)
        json_dir = tmp_path / "json"
        json_dir.mkdir(exist_ok=True)
        extra = _bl_rows() + [
            _bl_row("ff11000000000099", "9999999X", "OSD",
                    "fy_2025_supplemental", 123.0),
        ]
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            payload = _emit_years_matrix(
                json_dir=json_dir,
                con=con,
                all_prog_rows=_all_prog_rows(),
                detail_rows=_detail_rows(),
                bl_rows=extra,
                cited_fact_ids=_cited_fact_ids() | {"ff11000000000099"},
            )
        finally:
            con.close()
        assert "fy_2025_supplemental" not in payload["amount_types"]


# ---------------------------------------------------------------------------
# (b) program cells — workbook fact_ids
# ---------------------------------------------------------------------------


class TestProgramCells:
    def test_fy24_cell_single_row_workbook_fid(self, tmp_path):
        payload = _emit(tmp_path)
        cell = _program(payload, "0601101E")["cells"]["fy_2024_actuals"]
        assert cell == {"v": 100000.0, "fid": W_DARPA_24}

    def test_org_translation_cybercom(self, tmp_path):
        """CYBERCOM program's cells resolve via workbook org CYBER."""
        payload = _emit(tmp_path)
        cell = _program(payload, "0303140K")["cells"]["fy_2024_actuals"]
        assert cell == {"v": 30000.0, "fid": W_CYBER_24}

    # ---- (d) derived fallbacks ------------------------------------------------

    def test_multirow_trajectory_cell_uses_derived_fid(self, tmp_path):
        """Two fy_2025_total lines → cell is the cited trajectory sum."""
        payload = _emit(tmp_path)
        cell = _program(payload, "0601101E")["cells"]["fy_2025_total"]
        assert cell == {"v": 200000.0, "fid": D_DARPA_25}

    def test_delta_cell_derived_fid(self, tmp_path):
        payload = _emit(tmp_path)
        cell = _program(payload, "0601101E")["cells"]["fy2526_change"]
        assert cell == {"v": 200000.0, "fid": D_DARPA_CHG}

    def test_pct_cell_has_no_fid(self, tmp_path):
        payload = _emit(tmp_path)
        cell = _program(payload, "0601101E")["cells"]["fy2526_pct_change"]
        assert cell == {"v": 100.0}

    def test_zeroed_fy26_renders_zero_not_missing(self, tmp_path):
        """A real 0.0 trajectory value is a value (zeroed program), not '–'."""
        payload = _emit(tmp_path)
        cell = _program(payload, "0602303A")["cells"]["fy_2026_total"]
        assert cell is not None
        assert cell["v"] == 0.0
        assert cell["fid"] == fact_id_derived(
            "trajectory", "0602303A|A", "fy2026_total"
        )

    # ---- (e) honest absences --------------------------------------------------

    def test_missing_values_absent_never_zero(self, tmp_path):
        """Army has no fy_2026_total budget line but DOES have a trajectory
        value (0.0 zeroed) — covered above. A truly missing amount_type
        (fy_2025_enacted for Army) must be absent, not 0."""
        payload = _emit(tmp_path)
        cells = _program(payload, "0602303A")["cells"]
        assert cells.get("fy_2025_enacted") is None

    def test_multirow_nontrajectory_cell_absent(self, tmp_path):
        """Two fy_2025_enacted lines and no derived citation for that
        amount_type → the cell is absent (never an uncited client-side sum)."""
        payload = _emit(tmp_path)
        cells = _program(payload, "0601101E")["cells"]
        assert cells.get("fy_2025_enacted") is None

    def test_no_cell_fabricates_zero(self, tmp_path):
        """Every emitted v corresponds to real data — the ONLY zero program
        cell in this fixture is Army's genuinely-zeroed fy_2026_total."""
        payload = _emit(tmp_path)
        zeros = []
        for org in payload["orgs"]:
            for p in org["programs"]:
                for at, cell in p["cells"].items():
                    if cell is not None and cell["v"] == 0.0:
                        zeros.append((p["pe_bli"], at))
        assert zeros == [("0602303A", "fy_2026_total")]


# ---------------------------------------------------------------------------
# (c) project sub-rows
# ---------------------------------------------------------------------------


class TestProjectCells:
    def test_project_cell_jbook_fid(self, tmp_path):
        payload = _emit(tmp_path)
        projects = _program(payload, "0601101E")["projects"]
        assert len(projects) == 1
        p1 = projects[0]
        assert p1["project_number"] == "P1"
        assert p1["title"] == "Project One"
        assert p1["cells"]["fy2024"] == {"v": 12.5, "fid": J_P1_PRIOR}

    def test_project_zero_amount_cell_state_b(self, tmp_path):
        """zero_amount rows have NO citation — cell carries xp, no fid."""
        payload = _emit(tmp_path)
        p1 = _program(payload, "0601101E")["projects"][0]
        cell = p1["cells"]["fy2026"]
        assert cell["v"] == 0.0
        assert cell.get("fid") is None
        assert cell["xp"] == "ProgramElement[1]/Project[1]"

    def test_project_missing_scenario_absent(self, tmp_path):
        payload = _emit(tmp_path)
        p1 = _program(payload, "0601101E")["projects"][0]
        assert p1["cells"].get("fy2025") is None

    def test_root_rows_are_not_projects(self, tmp_path):
        payload = _emit(tmp_path)
        for org in payload["orgs"]:
            for p in org["programs"]:
                for proj in p["projects"]:
                    assert proj["project_number"] is not None

    def test_program_without_details_has_empty_projects(self, tmp_path):
        payload = _emit(tmp_path)
        assert _program(payload, "0602303A")["projects"] == []


# ---------------------------------------------------------------------------
# (f)+(g) citation shards
# ---------------------------------------------------------------------------


def _citations_dict() -> dict:
    """Minimal citations.json-shaped dict covering the fixture fact_ids."""
    out = {}
    for fid in sorted(_cited_fact_ids()):
        out[fid] = {"kind": "workbook", "units": "USD thousands", "sha256": "x"}
    return out


class TestCiteShards:
    def test_shard_placement_and_union(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir(exist_ok=True)
        cits = _citations_dict()
        n = _emit_cite_shards(json_dir=json_dir, citations_dict=cits)
        shard_dir = json_dir / "cite-shards"
        assert shard_dir.exists()
        files = sorted(shard_dir.glob("*.json"))
        assert len(files) == n

        union: set[str] = set()
        for f in files:
            prefix = f.stem
            assert len(prefix) == 2
            data = json.loads(f.read_text())
            for fid in data:
                assert fid[:2] == prefix, f"{fid} misplaced in shard {prefix}"
            assert union.isdisjoint(data.keys())
            union.update(data.keys())
        assert union == set(cits.keys()), "shard union != citations keys"

    def test_shard_rows_identical_to_citations_dict(self, tmp_path):
        json_dir = tmp_path / "json"
        json_dir.mkdir(exist_ok=True)
        cits = _citations_dict()
        _emit_cite_shards(json_dir=json_dir, citations_dict=cits)
        for fid, obj in cits.items():
            shard = json.loads(
                (json_dir / "cite-shards" / f"{fid[:2]}.json").read_text()
            )
            assert shard[fid] == obj

    def test_matrix_fids_resolve_in_shards(self, tmp_path):
        """(f): every fid referenced by the matrix payload resolves in its
        shard file — the lazy-resolution contract for the /years/ page."""
        payload = _emit(tmp_path)
        json_dir = tmp_path / "json"
        _emit_cite_shards(json_dir=json_dir, citations_dict=_citations_dict())

        fids: set[str] = set()
        for org in payload["orgs"]:
            for p in org["programs"]:
                for cell in p["cells"].values():
                    if cell and cell.get("fid"):
                        fids.add(cell["fid"])
                for proj in p["projects"]:
                    for cell in proj["cells"].values():
                        if cell and cell.get("fid"):
                            fids.add(cell["fid"])
        assert fids, "matrix references no fact_ids — fixture broken"
        for fid in fids:
            shard_path = json_dir / "cite-shards" / f"{fid[:2]}.json"
            assert shard_path.exists(), f"shard missing for {fid}"
            assert fid in json.loads(shard_path.read_text())


# ---------------------------------------------------------------------------
# (h) size budget
# ---------------------------------------------------------------------------


class TestSizeBudget:
    def test_size_budget_guard_raises_loudly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(es, "_YEARS_MATRIX_MAX_BYTES", 10)
        with pytest.raises(ValueError, match="years_matrix"):
            _emit(tmp_path)
        # the budgets are checked before anything is written
        assert not (tmp_path / "json" / "years_matrix.json").exists()
        assert not (tmp_path / "json" / "years_matrix").exists()

    def test_budgets_are_the_pre_split_ones(self):
        """Q11: the 4 MiB cap is unchanged and now per file; what /years/
        downloads on open may not exceed the deployed single file's gzip
        (780,074 B, years_matrix.json in 916ae88e)."""
        assert es._YEARS_MATRIX_MAX_BYTES == 4 * 1024 * 1024
        assert es._YEARS_MATRIX_CORE_GZIP_MAX == 780_074

    def test_core_gzip_budget_guard_raises_loudly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(es, "_YEARS_MATRIX_CORE_GZIP_MAX", 10)
        with pytest.raises(ValueError, match="gzips to"):
            _emit(tmp_path, decade_grains=_decade_grains())
        assert not (tmp_path / "json" / "years_matrix.json").exists()

    def test_cap_is_measured_on_the_bytes_written(self, tmp_path):
        """The pre-split guard measured the compact encoding and shipped the
        spaced one (2,900,904 B measured, 3,178,320 B shipped on
        2026-10-04). Every file is now written in the encoding the guard
        measures."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        json_dir = tmp_path / "json"
        for rel, obj in es.split_years_matrix(payload).items():
            on_disk = (json_dir / rel).read_bytes()
            assert on_disk == json.dumps(
                obj, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"), rel

    def test_write_json_compact_refuses_over_cap_and_writes_nothing(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(es, "_YEARS_MATRIX_MAX_BYTES", 10)
        target = tmp_path / "x.json"
        with pytest.raises(ValueError, match="cap"):
            es._write_json_compact(target, {"a": "b" * 20})
        assert list(tmp_path.iterdir()) == []

    def test_write_json_compact_returns_the_bytes_written(self, tmp_path):
        target = tmp_path / "x.json"
        n = es._write_json_compact(target, {"b": 1, "a": [1, 2]})
        assert target.read_bytes() == b'{"a":[1,2],"b":1}'
        assert n == 17
        assert sorted(p.name for p in tmp_path.iterdir()) == ["x.json"]

    @pytest.mark.skipif(
        not (_ROOT / "data" / "site" / "json" / "years_matrix.json").exists(),
        reason="live export not present",
    )
    def test_live_payload_under_budget(self):
        """Pinned to the exporter's own constants so this test and the
        exporter never drift. A live export from before the #193 split
        (schema_version 1, one file) is held to the old single-file cap."""
        json_dir = _ROOT / "data" / "site" / "json"
        core_path = json_dir / "years_matrix.json"
        core = json.loads(core_path.read_text())
        if core.get("schema_version") == 1:
            assert core_path.stat().st_size < es._YEARS_MATRIX_MAX_BYTES
            return
        for rel in es._YEARS_MATRIX_FILES:
            size = (json_dir / rel).stat().st_size
            assert size <= es._YEARS_MATRIX_MAX_BYTES, f"{rel} is {size} bytes"
        core_gzip = len(gzip.compress(core_path.read_bytes(), compresslevel=9, mtime=0))
        assert core_gzip <= es._YEARS_MATRIX_CORE_GZIP_MAX, core_gzip


# ---------------------------------------------------------------------------
# Phase 5E Task 6: decade columns (edition-honest FY2015A…FY2026R)
# ---------------------------------------------------------------------------


class TestDecadeColumns:
    def test_no_decade_grains_no_decade_keys(self, tmp_path):
        """Backward compat: without decade grains the payload is byte-stable
        with the 5D shape — no decade_columns/decade_default_columns keys."""
        payload = _emit(tmp_path)
        assert "decade_columns" not in payload
        assert "decade_default_columns" not in payload

    def test_decade_columns_header_carries_edition(self, tmp_path):
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        cols = {c["key"]: c for c in payload["decade_columns"]}
        assert cols["fy2020a"] == {
            "key": "fy2020a", "fy": 2020, "kind": "actuals", "edition": 2022,
        }
        for c in payload["decade_columns"]:
            assert isinstance(c["edition"], int), f"{c['key']} missing edition"

    def test_decade_columns_only_emitted_columns(self, tmp_path):
        """Columns appear only when ≥1 cited cell exists among matrix
        programs (no dead all-dash columns); ordering is (fy, kind)."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        keys = [c["key"] for c in payload["decade_columns"]]
        assert keys == ["fy2015a", "fy2020a", "fy2025e", "fy2026r"]

    def test_decade_default_columns_spec_order(self, tmp_path):
        """Default set = FY(e-2)A per edition + latest-edition FY(L-1)E and
        FY(L)R, filtered to present columns (spec §1: ≈12 with the full
        2017–2026 edition run)."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        assert payload["decade_default_columns"] == [
            "fy2015a", "fy2020a", "fy2025e", "fy2026r",
        ]

    def test_fy2020a_cell_value_and_fid_from_pb2022(self, tmp_path):
        """The FY2020A cell comes from the PB2022 edition (PB(N+2) rule) —
        value + fid are the fct_decade_series grain's."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        cell = _program(payload, "0601101E")["cells"]["fy2020a"]
        assert cell == {"v": 150000.0, "fid": W_DEC_20A}
        col = next(c for c in payload["decade_columns"] if c["key"] == "fy2020a")
        assert col["edition"] == 2022

    def test_multi_source_grain_uses_derived_decade_fid(self, tmp_path):
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        cell = _program(payload, "0601101E")["cells"]["fy2015a"]
        assert cell == {"v": 90000.0, "fid": D_DEC_15A}

    def test_absent_edition_cell_absent_never_zero(self, tmp_path):
        """A PE absent from an edition has NO cell for that column — missing
        renders '–', never 0."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        army = _program(payload, "0602303A")["cells"]
        assert "fy2020a" not in army
        assert "fy2015a" not in army
        # and no decade cell anywhere fabricates a zero
        for org in payload["orgs"]:
            for p in org["programs"]:
                for key, cell in p["cells"].items():
                    if key[:2] == "fy" and key[-1] in "aer" and "_" not in key:
                        assert cell["v"] != 0.0 or key == "fy_2026_total"

    def test_uncited_decade_cell_absent(self, tmp_path):
        """A grain whose fid has no citation row NEVER becomes a cell."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        cyber = _program(payload, "0303140K")["cells"]
        assert "fy2020a" not in cyber

    def test_existing_columns_unchanged_by_decade(self, tmp_path):
        """amount_types / default_columns / delta_columns are byte-identical
        with and without decade grains — existing /years/ consumers render
        unchanged until Task 7 adopts the decade keys."""
        base_dir = tmp_path / "base"
        dec_dir = tmp_path / "dec"
        base_dir.mkdir()
        dec_dir.mkdir()
        base = _emit(base_dir)
        withd = _emit(dec_dir, decade_grains=_decade_grains())
        assert withd["amount_types"] == base["amount_types"]
        assert withd["default_columns"] == base["default_columns"]
        assert withd["delta_columns"] == base["delta_columns"]
        for key in ("fy2015a", "fy2020a", "fy2025e", "fy2026r"):
            assert key not in withd["amount_types"]

    def test_conflicting_edition_for_column_raises(self, tmp_path):
        """Two grains mapping one column key to different editions is data
        corruption (the edition-authoritative rule makes the mapping unique)
        — the exporter must fail loudly, never emit an ambiguous column."""
        bad = _decade_grains() + [
            ("0602303A", 2020, 2023, "actuals", 1.0, W_ARMY_24,
             "fy_2020_actuals", None, None),
        ]
        with pytest.raises(ValueError, match="edition"):
            _emit(tmp_path, decade_grains=bad)

    def test_decade_fids_resolve_in_shards(self, tmp_path):
        """Every decade cell fid resolves in its cite-shard (the /years/
        lazy-resolution contract extends to decade columns)."""
        payload = _emit(tmp_path, decade_grains=_decade_grains())
        json_dir = tmp_path / "json"
        _emit_cite_shards(json_dir=json_dir, citations_dict=_citations_dict())
        for org in payload["orgs"]:
            for p in org["programs"]:
                for key, cell in p["cells"].items():
                    if cell and cell.get("fid"):
                        shard = json_dir / "cite-shards" / f"{cell['fid'][:2]}.json"
                        assert shard.exists(), f"shard missing for {cell['fid']}"
                        assert cell["fid"] in json.loads(shard.read_text())


class TestDecadeLive:
    """Live-payload checks (skipped until the 5E export lands)."""

    _live = _ROOT / "data" / "site" / "json" / "years_matrix.json"

    @pytest.mark.skipif(not _live.exists(), reason="live export not present")
    def test_live_decade_header_editions(self):
        payload = json.loads(self._live.read_text())
        if "decade_columns" not in payload:
            pytest.skip("live payload predates the 5E decade export")
        cols = {c["key"]: c for c in payload["decade_columns"]}
        # the edition-authoritative rule: actuals for FY N come from PB(N+2)
        assert cols["fy2020a"]["edition"] == 2022
        assert cols["fy2015a"]["edition"] == 2017
        for c in payload["decade_columns"]:
            if c["kind"] == "actuals":
                assert c["edition"] == c["fy"] + 2
            elif c["kind"] == "enacted":
                assert c["edition"] == c["fy"] + 1
            else:
                assert c["edition"] == c["fy"]

    @pytest.mark.skipif(not _live.exists(), reason="live export not present")
    def test_live_decade_default_columns(self):
        payload = json.loads(self._live.read_text())
        if "decade_default_columns" not in payload:
            pytest.skip("live payload predates the 5E decade export")
        # FY2015A…FY2024A + FY2025E + FY2026R (spec §1 — 12 columns)
        expected = [f"fy{y}a" for y in range(2015, 2025)] + ["fy2025e", "fy2026r"]
        assert payload["decade_default_columns"] == expected

    @pytest.mark.skipif(not _live.exists(), reason="live export not present")
    def test_live_decade_cell_fids_resolve_in_shards(self):
        payload = json.loads(self._live.read_text())
        if "decade_columns" not in payload:
            pytest.skip("live payload predates the 5E decade export")
        decade_keys = {c["key"] for c in payload["decade_columns"]}
        shard_dir = _ROOT / "data" / "site" / "json" / "cite-shards"
        checked = 0
        for org in payload["orgs"]:
            for p in org["programs"]:
                for key in decade_keys & set(p["cells"].keys()):
                    fid = p["cells"][key].get("fid")
                    assert fid, f"decade cell {p['pe_bli']}/{key} lacks fid"
                    shard = json.loads((shard_dir / f"{fid[:2]}.json").read_text())
                    assert fid in shard, f"{fid} unresolvable in shard"
                    checked += 1
                    if checked >= 25:
                        return
        assert checked, "no decade cells found in live payload"


# ---------------------------------------------------------------------------
# (g) program-lineage — sparse family_id overlay (Task 8, /years/ badge)
# ---------------------------------------------------------------------------


class TestFamilyOverlay:
    """The `families` kwarg threads a sparse pe_bli→family_id map into the
    program dicts. It is a UI-only overlay for the /years/ family-thread
    badge — never a column, cell value, or CSV field."""

    def test_family_id_present_only_for_mapped_pes(self, tmp_path):
        db_path = _make_duckdb_with_trajectory(tmp_path)
        json_dir = tmp_path / "json"
        json_dir.mkdir(exist_ok=True)
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            payload = _emit_years_matrix(
                json_dir=json_dir,
                con=con,
                all_prog_rows=_all_prog_rows(),
                detail_rows=_detail_rows(),
                bl_rows=_bl_rows(),
                cited_fact_ids=_cited_fact_ids(),
                # Two PEs share family 7; 0602303A is lone (absent from map).
                families={"0601101E": 7, "0303140K": 7},
            )
        finally:
            con.close()
        assert _program(payload, "0601101E")["family_id"] == 7
        assert _program(payload, "0303140K")["family_id"] == 7
        # Lone PE has NO family_id key (sparse — not None, absent).
        assert "family_id" not in _program(payload, "0602303A")

    def test_no_families_map_emits_no_family_id(self, tmp_path):
        """Default (no `families`) → no program carries family_id at all."""
        payload = _emit(tmp_path)  # _emit passes no families kwarg
        for org in payload["orgs"]:
            for p in org["programs"]:
                assert "family_id" not in p


# ---------------------------------------------------------------------------
# Families piece-1 follow-ups (ROADMAP #193, design §3): the piece-1 fence is
# lifted, so era procurement grains are /years/ cells like any other
# ---------------------------------------------------------------------------

ERA_17A = "f311000000000041"  # PB2019 FY2017 actuals added through the era map
ERA_19R = "f411000000000042"  # PB2019 FY2019 request added through the era map
ERA_FIDS = frozenset({ERA_17A, ERA_19R})


def _era_grains() -> list[tuple]:
    """Era grains look exactly like native ones (no era field). fy2017a and
    fy2019r are columns the native fixture grains do not have; fy2019r is
    not a default column, so it lands in the decade shard."""
    return [
        ("0601101E", 2017, 2019, "actuals", 777.0, ERA_17A,
         "fy_2017_actuals", None, None),
        ("0602303A", 2019, 2019, "request", 888.0, ERA_19R,
         "fy_2019_total", None, None),
    ]


class TestEraCellsRender:
    def test_the_emitter_takes_no_era_fence(self):
        """Piece 1's fence parameter is gone (design §3.3, §6.7): nothing can
        drop era grains from /years/ again by passing a set."""
        assert "era_grain_fids" not in inspect.signature(
            _emit_years_matrix
        ).parameters

    def test_era_cells_and_columns_render(self, tmp_path):
        payload = _emit(tmp_path, decade_grains=_decade_grains() + _era_grains(),
                        extra_cited=ERA_FIDS)
        assert _program(payload, "0601101E")["cells"]["fy2017a"] == {
            "v": 777.0, "fid": ERA_17A,
        }
        assert _program(payload, "0602303A")["cells"]["fy2019r"] == {
            "v": 888.0, "fid": ERA_19R,
        }
        cols = {c["key"]: c["edition"] for c in payload["decade_columns"]}
        assert cols["fy2017a"] == 2019 and cols["fy2019r"] == 2019

    def test_era_cells_reach_the_written_files(self, tmp_path):
        payload = _emit(tmp_path, decade_grains=_decade_grains() + _era_grains(),
                        extra_cited=ERA_FIDS)
        merged = _read_written(tmp_path / "json")
        assert _program(merged, "0601101E")["cells"]["fy2017a"]["fid"] == ERA_17A
        assert _program(merged, "0602303A")["cells"]["fy2019r"]["fid"] == ERA_19R
        assert _strip_split_keys(merged) == _strip_split_keys(payload)


# ---------------------------------------------------------------------------
# Families piece-1 follow-ups (ROADMAP #193, design §3.2–3.3): the core and
# two lazy shards
# ---------------------------------------------------------------------------

def _split_fixture_payload(tmp_path: Path) -> dict:
    """Native and era decade grains, projects and a family badge, so every
    tier of the split is non-empty (fy2019r is the one non-default decade
    column)."""
    db_path = _make_duckdb_with_trajectory(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return _emit_years_matrix(
            json_dir=json_dir,
            con=con,
            all_prog_rows=_all_prog_rows(),
            detail_rows=_detail_rows(),
            bl_rows=_bl_rows(),
            cited_fact_ids=_cited_fact_ids() | ERA_FIDS,
            decade_grains=_decade_grains() + _era_grains(),
            families={"0601101E": 7},
        )
    finally:
        con.close()


_YEARS_FILES = ("years_matrix.json", "years_matrix/decade.json", "years_matrix/detail.json")


def _written(json_dir: Path) -> dict[str, dict]:
    return {rel: json.loads((json_dir / rel).read_text()) for rel in _YEARS_FILES}


class TestShardSplit:
    def test_writes_the_core_and_exactly_two_shards(self, tmp_path):
        _split_fixture_payload(tmp_path)
        json_dir = tmp_path / "json"
        assert sorted(
            p.relative_to(json_dir).as_posix() for p in json_dir.rglob("*.json")
        ) == list(_YEARS_FILES)
        assert es._YEARS_MATRIX_FILES == _YEARS_FILES

    def test_core_holds_the_header_every_row_and_the_default_decade_cells(self, tmp_path):
        payload = _split_fixture_payload(tmp_path)
        core = _written(tmp_path / "json")["years_matrix.json"]
        assert core["schema_version"] == 2
        for key in ("program_units", "project_units", "amount_types", "delta_columns",
                    "default_columns", "project_scenarios", "decade_columns",
                    "decade_default_columns"):
            assert core[key] == payload[key], key
        defaults = set(core["decade_default_columns"])
        assert defaults == {"fy2015a", "fy2017a", "fy2020a", "fy2025e", "fy2026r"}
        rows = {p["pe_bli"]: p for o in core["orgs"] for p in o["programs"]}
        assert set(rows) == {"0601101E", "0602303A", "0303140K"}
        for row in rows.values():
            assert set(row) <= {"pe_bli", "title", "slug", "family_id", "np", "cells"}
            assert set(row["cells"]) <= defaults
        assert rows["0601101E"]["np"] == 1
        assert rows["0601101E"]["family_id"] == 7
        assert rows["0602303A"]["np"] == 0
        assert rows["0601101E"]["cells"]["fy2017a"] == {"v": 777.0, "fid": ERA_17A}

    def test_decade_shard_holds_only_the_other_decade_columns(self, tmp_path):
        _split_fixture_payload(tmp_path)
        decade = _written(tmp_path / "json")["years_matrix/decade.json"]
        assert decade["shard"] == "decade"
        assert decade["columns"] == ["fy2019r"]
        assert decade["rows"] == {
            "0602303A": {"cells": {"fy2019r": {"v": 888.0, "fid": ERA_19R}}},
        }

    def test_detail_shard_holds_amounts_deltas_and_projects(self, tmp_path):
        payload = _split_fixture_payload(tmp_path)
        detail = _written(tmp_path / "json")["years_matrix/detail.json"]
        assert detail["shard"] == "detail"
        assert detail["columns"] == payload["amount_types"] + payload["delta_columns"]
        darpa = detail["rows"]["0601101E"]
        assert darpa["cells"]["fy2526_change"] == {"v": 200000.0, "fid": D_DARPA_CHG}
        assert darpa["cells"]["fy2526_pct_change"] == {"v": 100.0}
        assert [p["project_number"] for p in darpa["projects"]] == ["P1"]
        decade_keys = {c["key"] for c in payload["decade_columns"]}
        for row in detail["rows"].values():
            assert not decade_keys & set(row.get("cells", {}))
        # a row without project sub-rows carries no "projects" key at all
        assert "projects" not in detail["rows"]["0602303A"]

    def test_merging_the_written_files_gives_the_payload(self, tmp_path):
        payload = _split_fixture_payload(tmp_path)
        merged = _read_written(tmp_path / "json")
        assert _strip_split_keys(merged) == _strip_split_keys(payload)
        for o in merged["orgs"]:
            for p in o["programs"]:
                assert p["np"] == len(p["projects"])

    def test_build_id_is_the_payload_content_hash(self, tmp_path):
        payload = _split_fixture_payload(tmp_path)
        files = _written(tmp_path / "json")
        want = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert {f["build_id"] for f in files.values()} == {want}
        manifest = {s["name"]: s for s in files["years_matrix.json"]["shards"]}
        assert set(manifest) == {"decade", "detail"}
        for name, entry in manifest.items():
            raw = (tmp_path / "json" / entry["path"]).read_bytes()
            assert entry["path"] == f"years_matrix/{name}.json"
            assert entry["bytes"] == len(raw)
            assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
            assert entry["columns"] == files[entry["path"]]["columns"]

    def test_merge_refuses_a_shard_from_another_build(self, tmp_path):
        _split_fixture_payload(tmp_path)
        files = _written(tmp_path / "json")
        stale = {**files["years_matrix/decade.json"], "build_id": "0" * 64}
        with pytest.raises(ValueError, match="build_id"):
            es.merge_years_matrix(files["years_matrix.json"], stale)

    def test_split_refuses_two_rows_with_one_key(self):
        payload = {
            "amount_types": [], "delta_columns": [],
            "orgs": [{"org": "N", "programs": [
                {"pe_bli": "0145", "title": "A", "cells": {}, "projects": []},
                {"pe_bli": "0145", "title": "B", "cells": {}, "projects": []},
            ]}],
        }
        with pytest.raises(ValueError, match="row key '0145'"):
            es.split_years_matrix(payload)

    def test_stale_shard_files_are_removed(self, tmp_path):
        stale = tmp_path / "json" / "years_matrix" / "stale.json"
        stale.parent.mkdir(parents=True)
        stale.write_text("{}")
        _split_fixture_payload(tmp_path)
        assert not stale.exists()

    @pytest.mark.skipif(
        not (_ROOT / "data" / "site" / "json" / "years_matrix.json").exists(),
        reason="live export not present",
    )
    def test_live_payload_round_trips(self):
        """On the live export: a pre-split file (schema 1) splits and merges
        back to itself; a split one merges from its three files, and its
        build_id is the hash of the merged view."""
        json_dir = _ROOT / "data" / "site" / "json"
        core = json.loads((json_dir / "years_matrix.json").read_text())
        if core.get("schema_version") == 1:
            files = es.split_years_matrix(core)
            merged = es.merge_years_matrix(*(files[rel] for rel in _YEARS_FILES))
            assert _strip_split_keys(merged) == _strip_split_keys(core)
            return
        v1 = {**_strip_split_keys(_read_written(json_dir)), "schema_version": 1}
        assert core["build_id"] == hashlib.sha256(
            json.dumps(v1, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


# ---------------------------------------------------------------------------
# ROADMAP #207 (follow-ups design §3.5): organization-split rows get their own
# decade and trajectory cells
# ---------------------------------------------------------------------------

W_20_DCSA_24 = "fa11000000000051"    # PB2026 P-1 FY2024 actuals, DCSA's line 20
W_20_DTRA_24 = "fa11000000000052"    # … DTRA's line 20
W_20_DCSA_25A = "fa11000000000058"   # two FY2025 total lines for DCSA: the
W_20_DCSA_25B = "fa11000000000059"   # cell falls back to the trajectory sum
W_20_DCSA_24A = "fb11000000000053"   # decade grain FY2024A (PB2026), DCSA
W_20_DTRA_24A = "fb11000000000054"   # decade grain FY2024A (PB2026), DTRA
W_20_DCSA_17A = "fc11000000000055"   # era grain FY2017A (PB2019), DCSA
W_0145_A_24A = "fd11000000000056"    # account-split control: 0145 in 1506N
W_0145_B_24A = "fd11000000000057"    # account-split control: 0145 in 1508N
# Minted by _build_derived_citation_rows with the account dropped for an
# organization-split key (ROADMAP #45): '20|DCSA', never '20|DCSA|0300D'.
D_20_DCSA_25 = fact_id_derived("trajectory", "20|DCSA", "fy2025_total")
D_20_DCSA_CHG = fact_id_derived("trajectory", "20|DCSA", "fy2526_change")
D_20_DTRA_25 = fact_id_derived("trajectory", "20|DTRA", "fy2025_total")
D_20_DTRA_CHG = fact_id_derived("trajectory", "20|DTRA", "fy2526_change")

_SPLIT_PROGRAMS = [
    # (pe_bli, org, exhibit_family, title, project_count, fy2024m,
    #  fully_reconciled, account, account_title)
    ("20", "DCSA", "procurement", "Vehicles", 0, None, False,
     "0300D", "Procurement, Defense-Wide"),
    ("20", "DTRA", "procurement", "Vehicles", 0, None, False,
     "0300D", "Procurement, Defense-Wide"),
    ("0145", "N", "procurement", "F/A-18E/F (Fighter) Hornet", 0, None, False,
     "1506N", "Aircraft Procurement, Navy"),
    ("0145", "N", "procurement", "General Purpose Bombs", 0, None, False,
     "1508N", "Procurement of Ammo, Navy & MC"),
]


def _make_duckdb_with_split_keys(tmp_path: Path) -> Path:
    db_path = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE fct_budget_trajectory (pe_bli varchar, organization varchar,"
        " account varchar, fy2024_actuals double, fy2025_total double,"
        " fy2026_total double, fy2526_change double, fy2526_pct_change double)"
    )
    con.execute(
        "INSERT INTO fct_budget_trajectory VALUES"
        " ('20', 'DCSA', '0300D', 2135.0, 2191.0, 2230.0, 39.0, 1.78),"
        " ('20', 'DTRA', '0300D', 356.0, 400.0, 410.0, 10.0, 2.5)"
    )
    con.execute(
        "CREATE TABLE dim_programs (pe_bli varchar, org varchar,"
        " exhibit_family varchar, title varchar, project_count integer,"
        " fy2024_actual_millions double, fully_reconciled boolean,"
        " account varchar, account_title varchar)"
    )
    con.executemany(
        "INSERT INTO dim_programs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", _SPLIT_PROGRAMS,
    )
    con.close()
    return db_path


def _split_bl_row(fid, org, amount, amount_type="fy_2024_actuals"):
    return (
        fid, "P-1", 2026, "0300D", "Procurement, Defense-Wide", org, "01",
        "Major Equipment", "20", "Vehicles", amount_type, amount,
        "USD thousands", "sha_wb", "Exhibit P-1", "Q10",
    )


def _emit_split_keys(tmp_path: Path) -> dict:
    db_path = _make_duckdb_with_split_keys(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    grains = [
        # organization-split grains carry no account (ROADMAP #45)
        ("20", 2024, 2026, "actuals", 2135.0, W_20_DCSA_24A, "fy_2024_actuals", None, "DCSA"),
        ("20", 2024, 2026, "actuals", 356.0, W_20_DTRA_24A, "fy_2024_actuals", None, "DTRA"),
        ("20", 2017, 2019, "actuals", 1057.0, W_20_DCSA_17A, "fy_2017_actuals", None, "DCSA"),
        # account-split grains carry the account and no organization
        ("0145", 2024, 2026, "actuals", 1000.0, W_0145_A_24A, "fy_2024_actuals", "1506N", None),
        ("0145", 2024, 2026, "actuals", 2000.0, W_0145_B_24A, "fy_2024_actuals", "1508N", None),
    ]
    cited = {
        W_20_DCSA_24, W_20_DTRA_24, W_20_DCSA_25A, W_20_DCSA_25B, W_20_DCSA_24A, W_20_DTRA_24A, W_20_DCSA_17A,
        W_0145_A_24A, W_0145_B_24A,
        D_20_DCSA_25, D_20_DCSA_CHG, D_20_DTRA_25, D_20_DTRA_CHG,
    }
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return _emit_years_matrix(
            json_dir=json_dir,
            con=con,
            all_prog_rows=list(_SPLIT_PROGRAMS),
            detail_rows=[],
            bl_rows=[
                _split_bl_row(W_20_DCSA_24, "DCSA", 2135.0),
                _split_bl_row(W_20_DTRA_24, "DTRA", 356.0),
                _split_bl_row(W_20_DCSA_25A, "DCSA", 1000.0, "fy_2025_total"),
                _split_bl_row(W_20_DCSA_25B, "DCSA", 1191.0, "fy_2025_total"),
            ],
            cited_fact_ids=cited,
            decade_grains=grains,
        )
    finally:
        con.close()


def _rows_by_slug(payload: dict) -> dict:
    return {
        p.get("slug") or p["pe_bli"]: p
        for o in payload["orgs"] for p in o["programs"]
    }


class TestOrgSplitRows:
    def test_org_split_rows_get_their_own_decade_cells(self, tmp_path):
        rows = _rows_by_slug(_emit_split_keys(tmp_path))
        dcsa, dtra = rows["20-DCSA"]["cells"], rows["20-DTRA"]["cells"]
        assert (dcsa["fy2024a"]["v"], dcsa["fy2024a"]["fid"]) == (2135.0, W_20_DCSA_24A)
        assert (dcsa["fy2017a"]["v"], dcsa["fy2017a"]["fid"]) == (1057.0, W_20_DCSA_17A)
        assert (dtra["fy2024a"]["v"], dtra["fy2024a"]["fid"]) == (356.0, W_20_DTRA_24A)
        assert "fy2017a" not in dtra

    def test_org_split_rows_get_their_trajectory_cells(self, tmp_path):
        rows = _rows_by_slug(_emit_split_keys(tmp_path))
        dcsa, dtra = rows["20-DCSA"]["cells"], rows["20-DTRA"]["cells"]
        assert dcsa["fy_2025_total"] == {"v": 2191.0, "fid": D_20_DCSA_25}
        assert dcsa["fy2526_change"] == {"v": 39.0, "fid": D_20_DCSA_CHG}
        assert dcsa["fy2526_pct_change"] == {"v": 1.78}
        assert dtra["fy_2025_total"] == {"v": 400.0, "fid": D_20_DTRA_25}
        assert dtra["fy2526_change"] == {"v": 10.0, "fid": D_20_DTRA_CHG}

    def test_org_split_single_line_cells_are_unchanged(self, tmp_path):
        rows = _rows_by_slug(_emit_split_keys(tmp_path))
        assert rows["20-DCSA"]["cells"]["fy_2024_actuals"] == {"v": 2135.0, "fid": W_20_DCSA_24}
        assert rows["20-DTRA"]["cells"]["fy_2024_actuals"] == {"v": 356.0, "fid": W_20_DTRA_24}

    def test_account_split_rows_keep_their_own_cells(self, tmp_path):
        """Control: the account axis is untouched by the fix."""
        payload = _emit_split_keys(tmp_path)
        by_account = {
            p["title"]: p["cells"]["fy2024a"]["fid"]
            for o in payload["orgs"] for p in o["programs"] if p["pe_bli"] == "0145"
        }
        assert by_account == {
            "F/A-18E/F (Fighter) Hornet": W_0145_A_24A,
            "General Purpose Bombs": W_0145_B_24A,
        }


class TestTitleLeakSurfaces:
    def test_every_years_file_is_scanned(self, tmp_path):
        """The title-override leak check re-reads every /years/ file: the
        core carries program titles and detail.json project titles."""
        json_dir = tmp_path / "json"
        (json_dir / "program_details").mkdir(parents=True)
        (json_dir / "program_details" / "0601101E.json").write_text("{}")
        surfaces = {
            p.relative_to(json_dir).as_posix() for p in es._title_leak_surfaces(json_dir)
        }
        assert set(_YEARS_FILES) <= surfaces
        assert {"programs.json", "program_details/0601101E.json"} <= surfaces


# ---------------------------------------------------------------------------
# The Python split and the JS merge are one contract (design §3.3–3.4)
# ---------------------------------------------------------------------------

SPLIT_FIXTURE_DIR = _ROOT / "tests" / "fixtures" / "years_matrix_split"
SPLIT_FIXTURES = {"basic": _split_fixture_payload, "split_keys": _emit_split_keys}


class TestCrossLanguageFixture:
    @pytest.mark.parametrize("name", sorted(SPLIT_FIXTURES))
    def test_committed_fixture_is_current(self, tmp_path, name):
        """tests/fixtures/years_matrix_split/<name>/ holds a fixture payload
        and its split; site/src/__tests__/years-matrix-shards.test.ts reads
        them to prove the JS merge (mergeYearsMatrix) inverts this split,
        split-key rows ("20-DCSA") included. Regenerate with the command in
        tests/fixtures/years_matrix_split/README.md."""
        payload = SPLIT_FIXTURES[name](tmp_path)
        here = SPLIT_FIXTURE_DIR / name
        assert json.loads((here / "payload.json").read_text()) == payload
        for rel, obj in es.split_years_matrix(payload).items():
            assert (here / rel).read_bytes() == es._canonical_json_bytes(obj), rel
