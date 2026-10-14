<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. -->

### Task 13: /years/ exporter — a core and two lazy shards, a compact writer measured on its own bytes, the era fence lifted, organization-split rows fixed (#193, #207)

**Spec:** `docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md` §3.1 (measured today), §3.2 (scheme A), §3.3 (exporter), §3.5 "Org-split decade lookup" (ROADMAP #207), §3.6 "Tests that change in the same commit series" (the Python half), §6.7 (`_emit_years_matrix` no longer takes `era_grain_fids`); owner answers Q10 and Q11 (binding, ROADMAP "Follow-ups first (owner, 2026-10-04)").
**Files:**
- Modify: `src/govbudget/export_site.py` — the module imports (anchor `import datetime`), the `_YEARS_MATRIX_MAX_BYTES` block (anchor `# Size budget for years_matrix.json`), new helpers inserted before `def _emit_years_matrix(` (anchor `_YEARS_DEFAULT_COLUMNS = [`), `_emit_years_matrix`'s signature, docstring, fence, `_acct_key` and write tail, the step-17 call in `_write_all_sidecars` (anchor `# 17. years_matrix.json`), the title-override leak scan (anchor `_leak_surfaces = [`), and two docstrings that still say /years/ skips era grains (`_build_decade_citation_rows`, anchor `era_grain_fids   — frozenset of the fids`; `_write_all_sidecars`, anchor `out-of-band era marker`; Task 16 later edits the `_write_all_sidecars` signature lines just above, not this paragraph)
- Modify (test): `tests/test_export_years_matrix.py` (imports, `_emit`, `TestMatrixStructure.test_creates_years_matrix_json`, `TestSizeBudget`, the era-fence section, plus four classes appended at the end); `tests/jbooks/test_export_site_pg.py` (`test_decade_matrix_columns`, `test_era_grain_fids_reach_the_fenced_emitters`); `tests/test_program_member_enrichment.py` (`test_years_matrix_projects_use_each_members_source`)
- Create: `tests/fixtures/years_matrix_split/README.md`, and the eight fixture files Step 7 generates under `tests/fixtures/years_matrix_split/{basic,split_keys}/` (`payload.json`, `years_matrix.json`, `years_matrix/decade.json`, `years_matrix/detail.json`)

Line numbers in this task are hints (anchor on the quoted text); Tasks 8, 9 and 12 edit `export_site.py` before this task runs and shift them.

**Interfaces:**
- Consumes: Task 1's worktree (`scripts/era/env.sh`, the 55432 test cluster, the `data/site` link). Nothing else: every edit anchors on text Tasks 2–12 do not touch.
- Produces (in `govbudget.export_site`):
  - `split_years_matrix(payload: dict) -> dict[str, dict]` — keys `"years_matrix.json"`, `"years_matrix/decade.json"`, `"years_matrix/detail.json"` (paths relative to `json/`);
  - `merge_years_matrix(core: dict, *shards: dict) -> dict` — the inverse up to `schema_version`, `build_id`, `shards` and each row's `np`; raises `ValueError` (message contains `build_id`) on a shard from another export; a schema-1 payload passed as the core merges to itself;
  - `years_matrix_row_key(program: dict) -> str` (`slug ?? pe_bli`), `_canonical_json_bytes(obj) -> bytes` (sorted keys, `(",", ":")`), `_write_json_compact(path: Path, obj) -> int`, `_write_years_matrix_files(json_dir: Path, files: dict[str, dict]) -> dict[str, int]`, `_title_leak_surfaces(json_dir: Path) -> list[Path]`;
  - constants `_YEARS_MATRIX_CORE = "years_matrix.json"`, `_YEARS_MATRIX_SHARD_DIR = "years_matrix"`, `_YEARS_MATRIX_SHARDS = ("decade", "detail")`, `_YEARS_MATRIX_FILES` (the three paths, core first), `_YEARS_MATRIX_SCHEMA_VERSION = 2`, `_YEARS_MATRIX_CORE_GZIP_MAX = 780_074`; `_YEARS_MATRIX_MAX_BYTES` stays `4 * 1024 * 1024`;
  - `_emit_years_matrix(*, json_dir, con, all_prog_rows, detail_rows, bl_rows, cited_fact_ids, decade_grains=None, families=None) -> dict` — no `era_grain_fids`; returns the v1-shaped payload (`schema_version` 1) and writes the three files;
  - the files: `json/years_matrix.json` (`schema_version` 2; the header; `build_id` = sha256 of `_canonical_json_bytes(payload)`; `shards` = `[{name, path, columns, bytes, sha256}]` for `decade` then `detail`; `orgs[].programs[]` = `{pe_bli, title, slug?, family_id?, np, cells}` with only `decade_default_columns` cells) and `json/years_matrix/{decade,detail}.json` (`{schema_version: 2, build_id, shard, columns, rows}`, rows keyed by `slug ?? pe_bli`, a detail row `{cells?, projects?}`);
  - `tests/fixtures/years_matrix_split/{basic,split_keys}/`, read by Task 14 (`years-matrix-shards.test.ts`) and Task 15 (`years-matrix-gate.test.mjs`); `tests/test_export_years_matrix.py` exports `SPLIT_FIXTURES` and `SPLIT_FIXTURE_DIR` for the README's regeneration command.
  - For Task 16 (#204): `_write_all_sidecars` no longer passes `era_grain_fids` to `_emit_years_matrix`, and the spy test is renamed `test_era_grain_fids_reach_the_lineage_emitter_only`; it asserts `{"lineage": sentinel, "years_matrix": "not passed"}`.

The payload is built exactly as before, as one dict, and only then split by
column tier: the core holds what the grid needs to open (the 12 default decade
columns), `decade.json` the other 18 decade columns, `detail.json` the PB2026
amount types, Δ, %Δ and the project rows. Every file carries one `build_id`, a
content hash, so byte-identity proofs keep working and the island (Task 14)
can tell a shard from another deploy. The 4 MiB cap is unchanged and now
applies to each file, measured on the exact bytes written: until now the guard
measured the compact encoding (2,900,904 B on 2026-10-04) while `_write_json`
shipped the spaced one (3,178,320 B). The core may not gzip above 780,074 B,
what the single file cost a reader on open (Python `gzip.compress(…, 9)` and
`gzip -9 -n` both measure 780,074 B for the deployed file; node's bundled zlib
reads 754,311 B, so the exporter's Python measure is the binding one).

The fence that dropped era grains goes, and `_acct_key` stops keeping the
account for organization-split codes (#207): on today's export the seven
rows 20-DCSA, 20-DTRA, 30-DMACT, 30-DTRA, 30-OSD, 500-DHRA and 500-DLA have no
decade cell at all and no `fy_2025_total`, `fy2526_change` or
`fy2526_pct_change` cell (read from `data/site/json/years_matrix.json`, built
2026-10-04 15:29).

- [ ] **Step 0: Record the pyflakes baseline of the files this task touches**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/export_site.py tests/test_export_years_matrix.py tests/jbooks/test_export_site_pg.py tests/test_program_member_enrichment.py | tail -3
```

Expected at base `7dccd983`: `Found 14 errors.` (10 in `export_site.py`, 4 in
the three test files; measured 2026-10-13). Earlier tasks may move the number:
write down what this prints, and Step 8 must print the same.

- [ ] **Step 1: Write the failing exporter tests**

All edits are in `tests/test_export_years_matrix.py`.

**Edit T13.1** — imports — `tests/test_export_years_matrix.py`. Replace this exact text:

```python
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from govbudget.config import ROOT as _ROOT
from govbudget.export_site import (
    _emit_cite_shards,
    _emit_years_matrix,
    fact_id_derived,
)
```

with:

```python
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
```

**Edit T13.2** — _emit helper — `tests/test_export_years_matrix.py`. Replace this exact text:

```python
def _emit(
    tmp_path: Path,
    decade_grains: list | None = None,
    *,
    era_grain_fids: frozenset[str] = frozenset(),
    extra_cited: frozenset[str] = frozenset(),
) -> dict:
    db_path = _make_duckdb_with_trajectory(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    # Passed only when set, so every other test drives the emitter's default.
    fence = {"era_grain_fids": era_grain_fids} if era_grain_fids else {}
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
            **fence,
        )
    finally:
        con.close()
    return payload
```

with:

```python
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
```

**Edit T13.3** — structure test reads merged files — `tests/test_export_years_matrix.py`. Replace this exact text:

```python
    def test_creates_years_matrix_json(self, tmp_path):
        payload = _emit(tmp_path)
        path = tmp_path / "json" / "years_matrix.json"
        assert path.exists(), "years_matrix.json was not created"
        on_disk = json.loads(path.read_text())
        assert on_disk == payload
```

with:

```python
    def test_creates_years_matrix_json(self, tmp_path):
        payload = _emit(tmp_path)
        path = tmp_path / "json" / "years_matrix.json"
        assert path.exists(), "years_matrix.json was not created"
        # #193: the core plus two shards, which merge back into the payload
        assert _strip_split_keys(_read_written(tmp_path / "json")) == (
            _strip_split_keys(payload)
        )
```

**Edit T13.4** — size budget class — `tests/test_export_years_matrix.py`. Replace this exact text:

```python
class TestSizeBudget:
    def test_size_budget_guard_raises_loudly(self, tmp_path, monkeypatch):
        import govbudget.export_site as es
        monkeypatch.setattr(es, "_YEARS_MATRIX_MAX_BYTES", 10)
        with pytest.raises(ValueError, match="years_matrix.json"):
            _emit(tmp_path)

    @pytest.mark.skipif(
        not (_ROOT / "data" / "site" / "json" / "years_matrix.json").exists(),
        reason="live export not present",
    )
    def test_live_payload_under_budget(self):
        """Phase 5E raised the budget 900 KB → 2 MB (spec §6: ~7 more decade
        columns × existing rows). Phase 5G raised it 2 MB → 4 MB across two
        rounds: the Navy J-books grew the detail-grade matrix ~462 → 813
        programs, then the Army/AF/SF archive round grew it 813 → ~1,741
        programs (~2.7–3.0 MB) at the SAME per-program density — legitimate
        corpus growth, not a design regression. Pinned to the exporter's own
        _YEARS_MATRIX_MAX_BYTES so this test and the exporter never drift."""
        import govbudget.export_site as es

        path = _ROOT / "data" / "site" / "json" / "years_matrix.json"
        size = path.stat().st_size
        assert size < es._YEARS_MATRIX_MAX_BYTES, (
            f"years_matrix.json is {size} bytes "
            f"(≥ {es._YEARS_MATRIX_MAX_BYTES}-byte budget)"
        )
```

with:

```python
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
```

**Edit T13.5** — era section — `tests/test_export_years_matrix.py`. Replace this exact text:

```python
# ---------------------------------------------------------------------------
# Families piece 1 (spec 2026-10-02 §6.2): era grains are fenced out of /years/
# ---------------------------------------------------------------------------

ERA_17A = "f311000000000041"  # PB2019 FY2017 actuals added through the era map
ERA_19R = "f411000000000042"  # PB2019 FY2019 request added through the era map
ERA_FIDS = frozenset({ERA_17A, ERA_19R})


def _era_grains() -> list[tuple]:
    """Era grains look exactly like native ones (no era field): only the
    out-of-band era_grain_fids set marks them. fy2017a and fy2019r are
    columns the native fixture grains do not have."""
    return [
        ("0601101E", 2017, 2019, "actuals", 777.0, ERA_17A,
         "fy_2017_actuals", None, None),
        ("0602303A", 2019, 2019, "request", 888.0, ERA_19R,
         "fy_2019_total", None, None),
    ]


class TestEraFence:
    def test_era_cells_would_render_without_the_fence(self, tmp_path):
        """Non-vacuity: unmarked, these cited grains DO become cells and
        columns, so the byte-identity below is the fence's doing."""
        payload = _emit(tmp_path, decade_grains=_decade_grains() + _era_grains(),
                        extra_cited=ERA_FIDS)
        assert _program(payload, "0601101E")["cells"]["fy2017a"] == {
            "v": 777.0, "fid": ERA_17A,
        }
        assert "fy2019r" in {c["key"] for c in payload["decade_columns"]}

    def test_era_grains_leave_years_matrix_byte_identical(self, tmp_path):
        base_dir = tmp_path / "base"
        era_dir = tmp_path / "era"
        base_dir.mkdir()
        era_dir.mkdir()
        base = _emit(base_dir, decade_grains=_decade_grains())
        fenced = _emit(era_dir, decade_grains=_decade_grains() + _era_grains(),
                       era_grain_fids=ERA_FIDS, extra_cited=ERA_FIDS)
        assert fenced == base
        assert (era_dir / "json" / "years_matrix.json").read_bytes() == (
            base_dir / "json" / "years_matrix.json"
        ).read_bytes()

    def test_era_only_grains_add_no_decade_header(self, tmp_path):
        payload = _emit(tmp_path, decade_grains=_era_grains(),
                        era_grain_fids=ERA_FIDS, extra_cited=ERA_FIDS)
        assert "decade_columns" not in payload
        assert "decade_default_columns" not in payload
```

with:

```python
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
```

Then append to the end of `tests/test_export_years_matrix.py`, two blank lines after its last line
(the `assert _strip_split_keys(merged) == _strip_split_keys(payload)` that
Edit T13.5 wrote):

```python
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
```

- [ ] **Step 2: Run them and watch them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . pytest tests/test_export_years_matrix.py -q
```

Expected: `23 failed, 42 passed` (measured on a scratch copy of the base tree
with the live `data/site` link; without the link the five live checks skip and
it reads `22 failed, 38 passed, 5 skipped`). The 23 failures, by kind:
- `AttributeError: module 'govbudget.export_site' has no attribute …`
  (`_YEARS_MATRIX_CORE_GZIP_MAX`, `split_years_matrix`, `_write_json_compact`,
  `_title_leak_surfaces`): the five new `TestSizeBudget` tests,
  `test_split_refuses_two_rows_with_one_key`, `test_live_payload_round_trips`
  and `TestTitleLeakSurfaces`;
- `FileNotFoundError: … json/years_matrix/decade.json`:
  `test_creates_years_matrix_json`, `test_era_cells_reach_the_written_files`
  and six `TestShardSplit` tests (core, decade, detail, merging, build id,
  merge refusal);
- `test_writes_the_core_and_exactly_two_shards`:
  `assert ['years_matrix.json'] == [...]`;
- `test_stale_shard_files_are_removed`: `assert not True` (the stale file
  survives);
- `test_the_emitter_takes_no_era_fence`:
  `assert 'era_grain_fids' not in mappingproxy(...)`;
- `TestOrgSplitRows`: `KeyError: 'fy2024a'` and `KeyError: 'fy_2025_total'`
  (its two control cases pass);
- `TestCrossLanguageFixture` `[basic]` and `[split_keys]`: `FileNotFoundError`
  on their `payload.json` (Step 7 writes them).

- [ ] **Step 3: Write the failing PG-export and member tests**

**Edit T13.7** — decade matrix columns — `tests/jbooks/test_export_site_pg.py`. Replace this exact text:

```python
def test_decade_matrix_columns(pg_dsn, tmp_path):
    """years_matrix.json carries the decade columns with per-column edition
    and per-cell fids."""
    site, fids = _run_decade_export(pg_dsn, tmp_path)
    matrix = json.loads(
        (site / "json" / "years_matrix.json").read_text())
```

with:

```python
def test_decade_matrix_columns(pg_dsn, tmp_path):
    """years_matrix.json carries the decade columns with per-column edition
    and per-cell fids. Since ROADMAP #193 the cells are split across the core
    and its two shards, so this reads the merged view."""
    from govbudget.export_site import merge_years_matrix

    site, fids = _run_decade_export(pg_dsn, tmp_path)
    json_dir = site / "json"
    matrix = merge_years_matrix(
        json.loads((json_dir / "years_matrix.json").read_text()),
        *(
            json.loads((json_dir / "years_matrix" / f"{name}.json").read_text())
            for name in ("decade", "detail")
        ),
    )
```

**Edit T13.8** — spy test — `tests/jbooks/test_export_site_pg.py`. Replace this exact text:

```python
def test_era_grain_fids_reach_the_fenced_emitters(pg_dsn, tmp_path, monkeypatch):
    """Families piece 1 (spec 2026-10-02 §6.2): export_site hands the decade
    tier's out-of-band era marker to the lineage and /years/ emitters, the
    only two readers of it. A sentinel set stands in for the tier's own."""
    import govbudget.export_site as es

    sentinel = frozenset({"e0a0000000000001"})
    real_tier = es._build_decade_citation_rows
    seen: dict[str, frozenset | None] = {}

    def tier(**kwargs):
        bl, cit, grains, side, _era = real_tier(**kwargs)
        return bl, cit, grains, side, sentinel

    def spy(name, real):
        def wrapper(**kwargs):
            seen[name] = kwargs.get("era_grain_fids")
            return real(**kwargs)
        return wrapper

    monkeypatch.setattr(es, "_build_decade_citation_rows", tier)
    monkeypatch.setattr(es, "_emit_lineage", spy("lineage", es._emit_lineage))
    monkeypatch.setattr(
        es, "_emit_years_matrix", spy("years_matrix", es._emit_years_matrix))
    _run_decade_export(pg_dsn, tmp_path)
    assert seen == {"lineage": sentinel, "years_matrix": sentinel}
```

with:

```python
def test_era_grain_fids_reach_the_lineage_emitter_only(pg_dsn, tmp_path, monkeypatch):
    """Families piece 1 (spec 2026-10-02 §6.2): export_site hands the decade
    tier's out-of-band era marker to the lineage emitter. Since the
    follow-ups lifted the /years/ fence (ROADMAP #193), lineage is its only
    reader: the /years/ emitter gets no era set at all. A sentinel set
    stands in for the tier's own."""
    import govbudget.export_site as es

    sentinel = frozenset({"e0a0000000000001"})
    real_tier = es._build_decade_citation_rows
    seen: dict[str, object] = {}

    def tier(**kwargs):
        bl, cit, grains, side, _era = real_tier(**kwargs)
        return bl, cit, grains, side, sentinel

    def spy(name, real):
        def wrapper(**kwargs):
            seen[name] = kwargs.get("era_grain_fids", "not passed")
            return real(**kwargs)
        return wrapper

    monkeypatch.setattr(es, "_build_decade_citation_rows", tier)
    monkeypatch.setattr(es, "_emit_lineage", spy("lineage", es._emit_lineage))
    monkeypatch.setattr(
        es, "_emit_years_matrix", spy("years_matrix", es._emit_years_matrix))
    _run_decade_export(pg_dsn, tmp_path)
    assert seen == {"lineage": sentinel, "years_matrix": "not passed"}
```

**Edit T13.9** — member years — `tests/test_program_member_enrichment.py`. Replace this exact text:

```python
def test_years_matrix_projects_use_each_members_source(member_export):
    years = json.loads((member_export / 'json/years_matrix.json').read_text())
```

with:

```python
def test_years_matrix_projects_use_each_members_source(member_export):
    # ROADMAP #193: project rows live in the detail shard; read the merged view.
    from govbudget.export_site import merge_years_matrix

    json_dir = member_export / 'json'
    years = merge_years_matrix(
        json.loads((json_dir / 'years_matrix.json').read_text()),
        *(json.loads((json_dir / 'years_matrix' / f'{name}.json').read_text())
          for name in ('decade', 'detail')),
    )
```

- [ ] **Step 4: Run them and watch them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_pg.py -q -k "decade_matrix_columns or era_grain_fids"
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_program_member_enrichment.py -q
```

Expected: `2 failed, 44 deselected` (more deselected if an earlier task added
tests to that file) — `test_decade_matrix_columns` with `ImportError: cannot
import name 'merge_years_matrix'`, and
`test_era_grain_fids_reach_the_lineage_emitter_only` with
`{'years_matrix': frozenset({'e0a0000000000001'})} != {'years_matrix': 'not passed'}`.
Then `1 failed, 6 passed`, the failure the same `ImportError`.

- [ ] **Step 5: Implement the split, the writer, the budgets, the fence lift and the org-split fix in `src/govbudget/export_site.py`**

First check which of the two imports an earlier task may already have added:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && grep -nE '^import (gzip|os)$' src/govbudget/export_site.py
```

Expected at base: no output. Apply Edit 13.1a only if `import gzip` is
missing and Edit 13.1b only if `import os` is missing; apply every other edit.

**Edit 13.1a** — import gzip — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
import datetime
import hashlib
```

with:

```python
import datetime
import gzip
import hashlib
```

**Edit 13.1b** — import os — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
import json
import re
```

with:

```python
import json
import os
import re
```

**Edit 13.2** — cap comment — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
# Size budget for years_matrix.json (fetched lazily by the /years/ client
# island). Phase 5E raised the 5D 900 KB budget to 2 MB raw (5E spec §6:
# the decade adds ~7 columns × existing rows, same lazy-fetch pattern).
# Phase 5G (Navy round) confirmed ~2 KB/program at 813 programs (~1.53 MB).
# Phase 5G (Army/AF/SF archive round) grew the detail-grade matrix to 1,741
# programs at ~1.6 KB/program → ~2.74 MB: the SAME per-program density, just
# more programs (Army 'A' + Air Force/Space Force 'F' J-book detail landed).
# Budget raised to 4 MB, which still catches a doubling from here (1,741 →
# ~2,540 programs) — a regression in the matrix design, not corpus growth.
# Loud guard — a payload over budget beyond linear program growth means the
# matrix design regressed, not that the budget should move.
_YEARS_MATRIX_MAX_BYTES = 4 * 1024 * 1024
```

with:

```python
# Size budget for EACH /years/ file (the core and its two lazy shards, all
# fetched by the /years/ client island). Phase 5E raised the 5D 900 KB budget
# to 2 MB raw (5E spec §6: the decade adds ~7 columns × existing rows, same
# lazy-fetch pattern). Phase 5G (Navy round) confirmed ~2 KB/program at 813
# programs (~1.53 MB). Phase 5G (Army/AF/SF archive round) grew the
# detail-grade matrix to 1,741 programs at ~1.6 KB/program → ~2.74 MB: the
# SAME per-program density, just more programs. Budget raised to 4 MB, which
# still catches a doubling from there — a regression in the matrix design,
# not corpus growth. Loud guard: never raise it.
#
# Families piece-1 follow-ups (ROADMAP #193, design §3.3, Q11): the cap now
# applies per file and is measured on the exact bytes written
# (_canonical_json_bytes). Until the split the guard measured the compact
# encoding while _write_json shipped the spaced one (2,900,904 B measured,
# 3,178,320 B shipped on 2026-10-04).
_YEARS_MATRIX_MAX_BYTES = 4 * 1024 * 1024

# What /years/ downloads on open (the core, gzip level 9 — Python's gzip and
# `gzip -9 -n` agree byte for byte) may not exceed what the single pre-split
# file cost: 780,074 B, years_matrix.json as deployed in 916ae88e. The split
# exists so era history costs nothing until a reader asks for it (Q11).
_YEARS_MATRIX_CORE_GZIP_MAX = 780_074
```

**Edit 13.3** — helpers before _emit_years_matrix — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
# Default visible columns (spec §1: FY24A, FY25T, FY26T, Δ, %Δ).
_YEARS_DEFAULT_COLUMNS = [
    "fy_2024_actuals",
    "fy_2025_total",
    "fy_2026_total",
    "fy2526_change",
    "fy2526_pct_change",
]


def _emit_years_matrix(
```

with:

```python
# Default visible columns (spec §1: FY24A, FY25T, FY26T, Δ, %Δ).
_YEARS_DEFAULT_COLUMNS = [
    "fy_2024_actuals",
    "fy_2025_total",
    "fy_2026_total",
    "fy2526_change",
    "fy2526_pct_change",
]

# The /years/ files (families piece-1 follow-ups design §3.2, scheme A;
# ROADMAP #193), relative to json/. The core keeps the pre-split name, so the
# build-time readers (getProgramDecadeCells reads fy2024a and fy2026r, both
# default columns; getDecadeEditions reads the header), the /coverage/
# derivation sentence and the live-asset probe still name the same file.
_YEARS_MATRIX_CORE = "years_matrix.json"
_YEARS_MATRIX_SHARD_DIR = "years_matrix"
_YEARS_MATRIX_SHARDS = ("decade", "detail")
_YEARS_MATRIX_FILES = (
    _YEARS_MATRIX_CORE,
    *(f"{_YEARS_MATRIX_SHARD_DIR}/{name}.json" for name in _YEARS_MATRIX_SHARDS),
)
_YEARS_MATRIX_SCHEMA_VERSION = 2


def _canonical_json_bytes(obj) -> bytes:
    """The ONE encoding every /years/ file is written in and measured on:
    compact separators, sorted keys, json's default ASCII escaping."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def years_matrix_row_key(program: dict) -> str:
    """A /years/ row's identity across the core and its shards: the page slug
    of a split-key row (Task E3 / ROADMAP #45), else the bare pe_bli — the
    `slug ?? pe_bli` the client island keys rows by. Unique: split rows carry
    slugs."""
    return program.get("slug") or program["pe_bli"]


def split_years_matrix(payload: dict) -> dict[str, dict]:
    """Split the v1-shaped /years/ payload into the core and two lazy shards
    (design §3.2, scheme A), keyed by path relative to json/:

      years_matrix.json          the header, every row (pe_bli, title, slug?,
                                 family_id?, np = its project count) and the
                                 cells of decade_default_columns: everything
                                 the grid needs to open
      years_matrix/decade.json   the other decade columns' cells
      years_matrix/detail.json   the PB2026 amount-type, Δ and %Δ cells and
                                 the project sub-rows

    Shard rows are keyed by years_matrix_row_key and carry only what that
    row has. Every file carries build_id, the sha256 of the canonical v1
    payload: a content hash, never a timestamp, so byte-identity proofs keep
    working and the island can tell a shard from another export. The core's
    `shards` manifest lists each shard's name, path, columns, bytes and
    sha256 (of the canonical encoding, i.e. of the file written).

    Pure. merge_years_matrix(core, *shards) is its inverse up to the keys the
    split adds: schema_version, build_id, shards, and np on rows.
    """
    build_id = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    core_cols = set(payload.get("decade_default_columns", []))
    lazy_decade = [
        c["key"] for c in payload.get("decade_columns", [])
        if c["key"] not in core_cols
    ]
    detail_cols = [*payload["amount_types"], *payload["delta_columns"]]
    tier = {k: "core" for k in core_cols}
    tier.update({k: "decade" for k in lazy_decade})
    tier.update({k: "detail" for k in detail_cols})
    rows: dict[str, dict] = {name: {} for name in _YEARS_MATRIX_SHARDS}
    seen: set[str] = set()
    core_orgs = []
    for org in payload["orgs"]:
        core_programs = []
        for program in org["programs"]:
            key = years_matrix_row_key(program)
            if key in seen:
                raise ValueError(
                    f"years_matrix row key {key!r} appears twice: shard rows"
                    " are keyed by slug ?? pe_bli, so two rows sharing it"
                    " would merge into one"
                )
            seen.add(key)
            by_tier: dict[str, dict] = {"core": {}, "decade": {}, "detail": {}}
            for col, cell in program["cells"].items():
                where = tier.get(col)
                if where is None:
                    raise ValueError(
                        f"years_matrix cell {key}/{col} belongs to no file: it"
                        " is neither a decade column nor an amount-type or Δ"
                        " column of the header"
                    )
                by_tier[where][col] = cell
            row = {k: v for k, v in program.items() if k not in ("cells", "projects")}
            row["np"] = len(program["projects"])
            row["cells"] = by_tier["core"]
            core_programs.append(row)
            if by_tier["decade"]:
                rows["decade"][key] = {"cells": by_tier["decade"]}
            detail: dict = {}
            if by_tier["detail"]:
                detail["cells"] = by_tier["detail"]
            if program["projects"]:
                detail["projects"] = program["projects"]
            if detail:
                rows["detail"][key] = detail
        core_orgs.append({**org, "programs": core_programs})
    columns = {"decade": lazy_decade, "detail": detail_cols}
    shards = {
        name: {
            "schema_version": _YEARS_MATRIX_SCHEMA_VERSION,
            "build_id": build_id,
            "shard": name,
            "columns": columns[name],
            "rows": rows[name],
        }
        for name in _YEARS_MATRIX_SHARDS
    }
    manifest = []
    for name in _YEARS_MATRIX_SHARDS:
        data = _canonical_json_bytes(shards[name])
        manifest.append({
            "name": name,
            "path": f"{_YEARS_MATRIX_SHARD_DIR}/{name}.json",
            "columns": columns[name],
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    core = {k: v for k, v in payload.items() if k != "orgs"}
    core.update({
        "schema_version": _YEARS_MATRIX_SCHEMA_VERSION,
        "build_id": build_id,
        "shards": manifest,
        "orgs": core_orgs,
    })
    out = {_YEARS_MATRIX_CORE: core}
    for name in _YEARS_MATRIX_SHARDS:
        out[f"{_YEARS_MATRIX_SHARD_DIR}/{name}.json"] = shards[name]
    return out


def merge_years_matrix(core: dict, *shards: dict) -> dict:
    """The /years/ grid as the island sees it once shards have loaded: the
    core with each shard's cells, and the detail shard's project rows, put
    back on their rows. Rows a shard does not name keep what the core gave
    them (a core row has no projects, so they default to []; a pre-split,
    schema-1 payload passed as the core therefore merges to itself). Raises
    when a shard carries another build_id: a shard from one export never
    fills a core from another.

    Mirrored key for key by mergeYearsMatrix in
    site/src/lib/years-matrix-shards.mjs (the island and the yearsmatrix
    gate); tests/fixtures/years_matrix_split/ pins the pair."""
    for shard in shards:
        if shard.get("build_id") != core.get("build_id"):
            raise ValueError(
                f"years_matrix shard {shard.get('shard')!r} carries build_id"
                f" {shard.get('build_id')!r} but the core carries"
                f" {core.get('build_id')!r}: files from two exports"
            )
    merged = {k: v for k, v in core.items() if k != "orgs"}
    orgs = []
    for org in core["orgs"]:
        programs = []
        for program in org["programs"]:
            key = years_matrix_row_key(program)
            cells = dict(program["cells"])
            projects: list = program.get("projects", [])
            for shard in shards:
                row = shard["rows"].get(key)
                if row is None:
                    continue
                cells.update(row.get("cells", {}))
                if "projects" in row:
                    projects = row["projects"]
            programs.append({**program, "cells": cells, "projects": projects})
        orgs.append({**org, "programs": programs})
    merged["orgs"] = orgs
    return merged


def _write_json_compact(path: Path, obj) -> int:
    """Write obj as _canonical_json_bytes through a temporary file and
    os.replace, refusing (ValueError, nothing written) when the encoding is
    over _YEARS_MATRIX_MAX_BYTES. Returns the bytes written: the guard and
    the shipped file measure the same bytes."""
    data = _canonical_json_bytes(obj)
    if len(data) > _YEARS_MATRIX_MAX_BYTES:
        raise ValueError(
            f"{path.name} would be {len(data)} bytes, over the"
            f" {_YEARS_MATRIX_MAX_BYTES}-byte cap per /years/ file; nothing"
            " written. Do not raise the cap."
        )
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return len(data)


def _write_years_matrix_files(json_dir: Path, files: dict[str, dict]) -> dict[str, int]:
    """Check every /years/ budget, then write the files: json/years_matrix/
    is removed and rewritten whole, so no stale shard can ship (prepare-assets
    mirrors the directory the same way), the shards first and the core, whose
    manifest describes them, last. Returns {path: bytes written}."""
    encoded = {rel: _canonical_json_bytes(obj) for rel, obj in files.items()}
    for rel, data in encoded.items():
        if len(data) > _YEARS_MATRIX_MAX_BYTES:
            raise ValueError(
                f"years_matrix file {rel} would be {len(data)} bytes, over the"
                f" {_YEARS_MATRIX_MAX_BYTES}-byte cap per file (spec §3,"
                " follow-ups design §3.3). The matrix design regressed; do not"
                " raise the cap."
            )
    core_gzip = len(gzip.compress(encoded[_YEARS_MATRIX_CORE], compresslevel=9, mtime=0))
    if core_gzip > _YEARS_MATRIX_CORE_GZIP_MAX:
        raise ValueError(
            f"years_matrix core {_YEARS_MATRIX_CORE} gzips to {core_gzip} bytes,"
            f" over the {_YEARS_MATRIX_CORE_GZIP_MAX}-byte budget for what /years/"
            " downloads on open (follow-ups design Q11). Move columns to a lazy"
            " shard; do not raise the budget."
        )
    shard_dir = json_dir / _YEARS_MATRIX_SHARD_DIR
    if shard_dir.exists():
        shutil.rmtree(shard_dir)
    shard_dir.mkdir(parents=True)
    written = {}
    for rel in sorted(files, key=lambda r: r == _YEARS_MATRIX_CORE):
        written[rel] = _write_json_compact(json_dir / rel, files[rel])
    return written


def _title_leak_surfaces(json_dir: Path) -> list[Path]:
    """The built files export_site's title-override leak check re-reads: the
    index files, every /years/ file (since the #193 split the core holds the
    program titles and detail.json the project titles) and every file in the
    per-entity sidecar directories. The caller skips files that do not
    exist."""
    surfaces = [
        json_dir / "programs.json",
        json_dir / "search_quick.json",
        json_dir / "feed.json",
        *(json_dir / rel for rel in _YEARS_MATRIX_FILES),
    ]
    for sub in ("program_details", "entity_details", "districts", "flows", "filings", "feed-sections"):
        d = json_dir / sub
        if d.is_dir():
            surfaces.extend(sorted(d.glob("*.json")))
    return surfaces


def _emit_years_matrix(
```

**Edit 13.4** — signature and docstring head — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
    decade_grains: list | None = None,
    families: dict[str, int] | None = None,
    era_grain_fids: frozenset[str] = frozenset(),
) -> dict:
    """Emit json/years_matrix.json — the /years/ CapIQ-style grid payload.

    era_grain_fids (families piece 1, spec 2026-10-02 §6.2): decade grains
    added through the reviewed era map are dropped BEFORE anything reads
    decade_grains, so the payload (cells, decade_columns, the header's
    edition map, decade_default_columns) is byte-identical to an export
    without them. Era procurement would add about 0.75 MB against the
    4 MiB cap and fail years-matrix leg g; carrying it needs the matrix
    sharded first (filed follow-up, spec §11).
```

with:

```python
    decade_grains: list | None = None,
    families: dict[str, int] | None = None,
) -> dict:
    """Emit the /years/ CapIQ-style grid: json/years_matrix.json (the core)
    and json/years_matrix/{decade,detail}.json (the lazy shards).

    The payload is built exactly as before, in memory, as ONE v1-shaped dict
    (the return value), and only then split by column tier
    (split_years_matrix; families piece-1 follow-ups design §3.2, scheme A,
    ROADMAP #193). Era procurement grains (PB2017–PB2023 lines a reviewed
    decision joined to a program) become cells like any other: piece 1's
    fence (spec 2026-10-02 §6.2) dropped them while the single file had no
    room for them, and the split leaves every file far under the 4 MiB cap,
    so a /years/ row now shows exactly its program page's decade points.
```

**Edit 13.5** — docstring tail — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
    Returns the payload dict (also written to disk). Raises ValueError when
    the serialized payload exceeds _YEARS_MATRIX_MAX_BYTES.
    """
    from collections import defaultdict

    # spec §6.2 fence: the matrix is built as if era grains did not exist.
    decade_grains = [
        g for g in (decade_grains or []) if g[5] not in era_grain_fids
    ]

    # program-lineage Task 8: sparse pe_bli→family_id overlay (UI-only badge).
```

with:

```python
    Returns the v1-shaped payload dict, which _write_years_matrix_files
    writes as the core and two shards. Raises ValueError when any file would
    exceed _YEARS_MATRIX_MAX_BYTES or the core would gzip above
    _YEARS_MATRIX_CORE_GZIP_MAX.
    """
    from collections import defaultdict

    # program-lineage Task 8: sparse pe_bli→family_id overlay (UI-only badge).
```

**Edit 13.6** — _acct_key — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
    def _acct_key(pe_bli: str, account: str | None) -> str | None:
        return account if pe_bli in ident.split_pe_blis else None
```

with:

```python
    # ROADMAP #207 (follow-ups design §3.5): the account is the discriminator
    # ONLY on an account-split key. Keeping it for every split key looked the
    # three organization-split codes' rows ('20', '30', '500') up under
    # ('20', '0300D', 'DCSA') while their decade grains sit under
    # ('20', None, 'DCSA'), so seven rows lost every decade cell, and it
    # minted the trajectory key '20|DCSA|0300D', which no citation carries
    # (_build_derived_citation_rows keys on is_account_split, ROADMAP #45).
    def _acct_key(pe_bli: str, account: str | None) -> str | None:
        return account if ident.is_account_split(pe_bli) else None
```

**Edit 13.7** — write tail — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len(raw.encode("utf-8")) > _YEARS_MATRIX_MAX_BYTES:
        raise ValueError(
            f"years_matrix.json is {len(raw.encode('utf-8'))} bytes — over the"
            f" {_YEARS_MATRIX_MAX_BYTES}-byte budget (spec §3). The matrix"
            " design regressed; do not raise the budget."
        )
    _write_json(json_dir / "years_matrix.json", payload)
    return payload
```

with:

```python
    _write_years_matrix_files(json_dir, split_years_matrix(payload))
    return payload
```

**Edit 13.8** — call site — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
        cited_fact_ids=_cited_fact_ids,
        decade_grains=decade_grains,
        era_grain_fids=era_grain_fids,
        # program-lineage Task 8: sparse pe_bli→family_id map (from
        # _load_lineage_for_export above). Drives the /years/ family-thread
        # badge — a UI-only overlay, NOT a column / cell value / CSV field.
        families=_lin_families,
    )
    n_files += 1
```

with:

```python
        cited_fact_ids=_cited_fact_ids,
        decade_grains=decade_grains,
        # program-lineage Task 8: sparse pe_bli→family_id map (from
        # _load_lineage_for_export above). Drives the /years/ family-thread
        # badge — a UI-only overlay, NOT a column / cell value / CSV field.
        families=_lin_families,
    )
    n_files += len(_YEARS_MATRIX_FILES)  # the core and its two shards (#193)
```

**Edit 13.9** — leak surfaces — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
        _leak_surfaces = [
            json_dir / "programs.json",
            json_dir / "search_quick.json",
            json_dir / "feed.json",
            json_dir / "years_matrix.json",
        ]
        for _sub in ("program_details", "entity_details", "districts", "flows", "filings", "feed-sections"):
            _d = json_dir / _sub
            if _d.is_dir():
                _leak_surfaces.extend(sorted(_d.glob("*.json")))
```

with:

```python
        _leak_surfaces = _title_leak_surfaces(json_dir)
```

**Edit 13.10** — decade tier docstring — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python
      era_grain_fids   — frozenset of the fids of the decade_grains added
                         through the map. Never serialized: decade_grains and
                         the sidecar decade_series keep their exact shape;
                         the lineage and /years/ emitters skip these fids
                         (spec §6.2 fences).
```

with:

```python
      era_grain_fids   — frozenset of the fids of the decade_grains added
                         through the map. Never serialized: decade_grains and
                         the sidecar decade_series keep their exact shape;
                         the lineage emitter skips these fids (spec §6.2
                         fence). /years/ shows them since ROADMAP #193 lifted
                         its fence.
```

**Edit 13.11** — sidecar writer docstring — `src/govbudget/export_site.py` (anchor on the quoted text). Replace this exact text:

```python

    era_grain_fids: the decade tier's out-of-band era marker (spec 2026-10-02
    §6.1). Never serialized; only the lineage and /years/ emitters read it,
    to keep era points off the surfaces this piece fences (§6.2)."""
```

with:

```python

    era_grain_fids: the decade tier's out-of-band era marker (spec 2026-10-02
    §6.1). Never serialized; only the lineage emitter reads it, to keep era
    points off the lineage funding lines (§6.2). /years/ shows era points
    since ROADMAP #193 lifted its fence."""
```

- [ ] **Step 6: Run the exporter tests: everything but the fixture check passes**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . pytest tests/test_export_years_matrix.py -q
```

Expected: `2 failed, 63 passed` — only
`TestCrossLanguageFixture::test_committed_fixture_is_current[basic]` and
`[split_keys]`, each with `FileNotFoundError` on its `payload.json`.

- [ ] **Step 7: Write the cross-language fixtures**

Create `tests/fixtures/years_matrix_split/README.md`:

````markdown
# /years/ split fixtures (ROADMAP #193)

Each directory holds one `_emit_years_matrix` fixture payload from
`tests/test_export_years_matrix.py` (`payload.json`, indented for reading) and
the three files `split_years_matrix` makes of it, byte for byte as the exporter
writes them (compact, so their bytes and sha256 match the core's manifest):

- `basic/` (`_split_fixture_payload`): native and era decade grains, project
  rows and a family badge; `fy2019r` is the one lazy decade column.
- `split_keys/` (`_emit_split_keys`): the organization-split code `20`
  (rows `20-DCSA`, `20-DTRA`) and the account-split code `0145`.

Three tests read them:

- `tests/test_export_years_matrix.py::TestCrossLanguageFixture` fails when the
  files no longer match the Python split;
- `site/src/__tests__/years-matrix-shards.test.ts` checks that the JS merge
  (`mergeYearsMatrix`, which the /years/ island runs) turns them back into
  `payload.json`;
- `site/scripts/gates/__tests__/years-matrix-gate.test.mjs` loads them through
  the yearsmatrix gate's loader.

After a deliberate change to the split, regenerate both directories from
`GovBudget/`:

```bash
uv run --project . python - <<'PY'
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests")
import test_export_years_matrix as t
from govbudget.export_site import _canonical_json_bytes, split_years_matrix
for name, build in t.SPLIT_FIXTURES.items():
    out = t.SPLIT_FIXTURE_DIR / name
    (out / "years_matrix").mkdir(parents=True, exist_ok=True)
    payload = build(Path(tempfile.mkdtemp()))
    (out / "payload.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for rel, obj in split_years_matrix(payload).items():
        (out / rel).write_bytes(_canonical_json_bytes(obj))
PY
```
````

Then run the command it documents:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'PY'
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests")
import test_export_years_matrix as t
from govbudget.export_site import _canonical_json_bytes, split_years_matrix
for name, build in t.SPLIT_FIXTURES.items():
    out = t.SPLIT_FIXTURE_DIR / name
    (out / "years_matrix").mkdir(parents=True, exist_ok=True)
    payload = build(Path(tempfile.mkdtemp()))
    (out / "payload.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for rel, obj in split_years_matrix(payload).items():
        (out / rel).write_bytes(_canonical_json_bytes(obj))
PY
find tests/fixtures/years_matrix_split -type f | sort
head -c 200 tests/fixtures/years_matrix_split/basic/years_matrix/decade.json; echo
```

Expected: the nine files, in this order —
`tests/fixtures/years_matrix_split/README.md`, then `basic/payload.json`,
`basic/years_matrix.json`, `basic/years_matrix/decade.json`,
`basic/years_matrix/detail.json`, and the same four under `split_keys/` —
then
`{"build_id":"8dad9afdc8fbf12f1a63191161a0c91b0103edf2a81e0d259c3ba279930e1d34","columns":["fy2019r"],"rows":{"0602303A":{"cells":{"fy2019r":{"fid":"f411000000000042","v":888.0}}}},"schema_version":2,"shard":"decade"}`
(the build id is the fixture payload's content hash, so it is the same on
every run; measured on the scratch copy).

- [ ] **Step 8: Run every touched test file, the neighbours that call the exporter, and pyflakes**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_years_matrix.py tests/jbooks/test_export_site_pg.py tests/test_program_member_enrichment.py tests/test_export_decade_era_map.py tests/jbooks/test_export_lineage.py tests/test_export_breakdowns.py -q
uvx --offline ruff check --isolated --select F,E9 src/govbudget/export_site.py tests/test_export_years_matrix.py tests/jbooks/test_export_site_pg.py tests/test_program_member_enrichment.py | tail -3
```

Expected: `177 passed` (65 + 46 + 7 + 24 + 13 + 22 — `tests/test_export_decade_era_map.py` holds Task 8's two added tests — measured on the scratch
copy; more if earlier tasks added tests to these files — the criterion is 0
failed), and the Step 0 count unchanged. `test_export_site_pg.py` shares the
55432 cluster: if another session is using it at the same moment, a run can
fail on a truncated PDF stream or a missing fixture value; re-run before
reading a failure as this task's.

- [ ] **Step 9: Measure the split on today's export (read-only)**

This reads `data/site/json/years_matrix.json` (the live export, schema 1,
built 2026-10-04) and splits it in memory: nothing is written and no lake or
DuckDB file is opened, so no SAM-window guard is needed.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'PY'
import gzip, json, os
from govbudget import export_site as es
src = os.path.join(os.environ["GOVBUDGET_DATA"], "site", "json", "years_matrix.json")
payload = json.load(open(src))
files = es.split_years_matrix(payload)
for rel in es._YEARS_MATRIX_FILES:
    data = es._canonical_json_bytes(files[rel])
    print(rel, len(data), len(gzip.compress(data, compresslevel=9, mtime=0)))
merged = es.merge_years_matrix(*(files[rel] for rel in es._YEARS_MATRIX_FILES))
strip = lambda v: {**{k: x for k, x in v.items() if k not in ("schema_version", "build_id", "shards")},
                   "orgs": [{**o, "programs": [{k: x for k, x in p.items() if k != "np"} for p in o["programs"]]} for o in v["orgs"]]}
print("round trip", strip(merged) == strip(payload))
PY
```

Expected (today's fenced payload, measured 2026-10-13):
`years_matrix.json 855969 263763`, `years_matrix/decade.json 900935 278811`,
`years_matrix/detail.json 1231643 284232`, `round trip True`. With the fence
lifted, a read-only simulation that gives every row its own sidecar's decade
points (the parity Task 15's leg j enforces) splits to 1,100,823 B / 344,303
gzip, 1,390,739 / 433,932 and 1,231,643 / 284,230: the largest file uses 33%
of the cap and the core 44% of its gzip budget. Task 21 measures the real
export.

- [ ] **Step 10: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/export_site.py GovBudget/tests/test_export_years_matrix.py GovBudget/tests/jbooks/test_export_site_pg.py GovBudget/tests/test_program_member_enrichment.py GovBudget/tests/fixtures/years_matrix_split && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(export): split /years/ into a core and two lazy shards, lift the era fence, fix organization-split rows (#193, #207)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
