<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Runs after Task 13. -->

### Task 16: Required `era_grain_fids` and the `build_lineage_flow` invariant (#204)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.7: `era_grain_fids` becomes a required keyword-only argument on `_emit_lineage`, `_emit_json_sidecars` and `_write_all_sidecars`; `_emit_years_matrix` no longer takes it (Task 13 removed it with the /years/ fence); an `inspect.signature` test asserts there is no default; the test callers are updated; an invariant assertion at the `build_lineage_flow` call (`export_site.py:13440`): no chosen amount fid is in `era_grain_fids`. Lands after §3 (Task 13).

**Files:**
- Modify: `src/govbudget/export_site.py` — a new function inserted before `def _emit_lineage(` (about line 11140); the signatures of `_emit_lineage` (anchor on `    cited_fact_ids: set[str],\n    era_grain_fids: frozenset[str] = frozenset(),\n) -> dict[str, dict]:`), `_emit_json_sidecars` (anchor on `) -> int:\n    """Emit all JSON sidecars to out_dir/json/.`) and `_write_all_sidecars` (anchor on `) -> int:\n    """Core sidecar writer; called from _emit_json_sidecars.`); the call after `lineage_flow_payload = build_lineage_flow(` (about line 13442)
- Modify: `tests/jbooks/test_export_lineage.py` (the `_emit` helper, about line 28)
- Modify: `tests/test_program_member_enrichment.py` (the `_emit_json_sidecars(` call, about line 140)
- Create: `tests/test_export_era_fences_required.py`
- Test: `tests/jbooks/test_export_site_pg.py` (append at the end)

Line numbers are the 2026-10-13 HEAD's; Task 13 edits `export_site.py` first, so anchor on the quoted text.

**Interfaces:**
Consumes: Task 13 — `_emit_years_matrix` no longer has an `era_grain_fids` parameter, and the `_emit_years_matrix(` call in `_write_all_sidecars` no longer passes it; `_write_all_sidecars` still receives `era_grain_fids` and passes it to `_emit_lineage`. `lineage.flow.build_lineage_flow` and `AMOUNT_FY`/`AMOUNT_MEASURE`, unchanged.
Produces:
- `_emit_lineage(*, …, cited_fact_ids: set[str], era_grain_fids: frozenset[str]) -> dict[str, dict]`, `_emit_json_sidecars(*, …, fy26_split_by_pe: dict | None = None, era_grain_fids: frozenset[str]) -> int`, `_write_all_sidecars(*, …, fy26_split_by_pe: dict | None = None, era_grain_fids: frozenset[str]) -> int` — no default; a caller that omits it gets a `TypeError`.
- `_assert_lineage_flow_has_no_era_amount(payload: dict, era_grain_fids: frozenset[str]) -> None` in `govbudget.export_site`: raises `RuntimeError("lineage flow: <n> FY2026 amount(s) chosen from an era grain (…)")` when any `payload["families"|"candidates"][*]["nodes"][*]["amount"]["fid"]` is in `era_grain_fids`; `_write_all_sidecars` calls it right after `build_lineage_flow`. Export output is unchanged (Task 21's P2 sees no difference from this task).

Measured for this task (2026-10-13 HEAD, before Task 13): `grep -rn "_emit_lineage(\|_emit_json_sidecars(\|_write_all_sidecars(" src tests scripts` → production calls at `export_site.py:3734` (`_emit_json_sidecars`, passes `era_grain_fids=era_grain_fids`), `:11445` (`_write_all_sidecars`, passes it) and `:13420` (`_emit_lineage`, passes it); test calls at `tests/jbooks/test_export_lineage.py:29` (the `_emit` helper, omits it) and `:303` (passes it), and `tests/test_program_member_enrichment.py:140` (omits it). All three definitions default it to `frozenset()` (`:11149`, `:11427`, `:11482`). `build_lineage_flow` (`src/govbudget/lineage/flow.py:286`) picks per identity the first `request` point with `fy == AMOUNT_FY` (2026) and `measure == AMOUNT_MEASURE` ("request") and puts it on the identity's node as `amount = {v, fid, fy, edition, basis, measure}` (`_layout`); a call with `families={"PRED": 1}`, no edges and one FY2026 request point returns `families[0]["nodes"][0]["amount"]["fid"]` equal to that point's fid. Test counts: `tests/jbooks/test_export_lineage.py` 13 passed, `tests/test_program_member_enrichment.py` 7 passed, `tests/jbooks/test_export_site_pg.py -k era_grain_fids` 1 passed.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_export_era_fences_required.py`:

```python
"""ROADMAP #204 (families piece-1 follow-ups spec 2026-10-04 §6.7): the era
fences are required arguments, and the /lineage/ flow asserts that no era
grain supplies its money column."""
from __future__ import annotations

import inspect

import pytest

from govbudget import export_site as es
from govbudget.lineage.flow import AMOUNT_FY, AMOUNT_MEASURE, build_lineage_flow

ERA = "e0a0000000000001"
NATIVE = "f0a0000000000002"


@pytest.mark.parametrize("name", ["_emit_lineage", "_emit_json_sidecars", "_write_all_sidecars"])
def test_era_grain_fids_is_a_required_keyword_only_argument(name):
    param = inspect.signature(getattr(es, name)).parameters["era_grain_fids"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty, f"{name} still defaults era_grain_fids"


def test_years_matrix_no_longer_takes_the_era_fence():
    # Task 13 lifted the /years/ fence; a stale parameter would read as a fence.
    assert "era_grain_fids" not in inspect.signature(es._emit_years_matrix).parameters


def _flow(fid: str) -> dict:
    return build_lineage_flow(
        edges=[], families={"PRED": 1}, titles_by_pe={"PRED": "Predecessor"},
        page_pes={"PRED"},
        decade_series_by_pe={"PRED": {"request": [{
            "fy": AMOUNT_FY, "v": 5.0, "fid": fid, "edition": 2026, "basis": "toa",
            "measure": AMOUNT_MEASURE}]}},
        cited_fact_ids={fid},
    )


def test_the_lineage_flow_accepts_a_native_amount():
    es._assert_lineage_flow_has_no_era_amount(_flow(NATIVE), frozenset({ERA}))


def test_the_lineage_flow_refuses_an_era_amount():
    with pytest.raises(RuntimeError, match=r"1 FY2026 amount\(s\) chosen from an era grain"):
        es._assert_lineage_flow_has_no_era_amount(_flow(ERA), frozenset({ERA}))
```

Append to `tests/jbooks/test_export_site_pg.py`:

```python


def test_the_lineage_flow_invariant_sees_the_tiers_era_marker(pg_dsn, tmp_path, monkeypatch):
    """ROADMAP #204: export_site checks build_lineage_flow's chosen amounts
    against the decade tier's own era set. A sentinel set stands in for it."""
    import govbudget.export_site as es

    sentinel = frozenset({"e0a0000000000001"})
    real_tier = es._build_decade_citation_rows
    real_check = es._assert_lineage_flow_has_no_era_amount
    seen: list[frozenset] = []

    def tier(**kwargs):
        bl, cit, grains, side, _era = real_tier(**kwargs)
        return bl, cit, grains, side, sentinel

    def check(payload, era_grain_fids):
        seen.append(era_grain_fids)
        return real_check(payload, era_grain_fids)

    monkeypatch.setattr(es, "_build_decade_citation_rows", tier)
    monkeypatch.setattr(es, "_assert_lineage_flow_has_no_era_amount", check)
    _run_decade_export(pg_dsn, tmp_path)
    assert seen == [sentinel]
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_era_fences_required.py tests/jbooks/test_export_site_pg.py -q -k "required or years_matrix_no_longer or lineage_flow" 2>&1 | tail -3
```

Expected: `6 failed, 1 passed`. The 3 signature cases fail on `assert param.default is inspect.Parameter.empty`, and the two flow tests and the Postgres test on `AttributeError: module 'govbudget.export_site' has no attribute '_assert_lineage_flow_has_no_era_amount'`. `test_years_matrix_no_longer_takes_the_era_fence` passes because Task 13 has landed; if it fails, Task 13 is not done: stop.

- [ ] **Step 2: Add the invariant**

In `src/govbudget/export_site.py`, replace:

```python
def _emit_lineage(
    *,
```

with:

```python
def _assert_lineage_flow_has_no_era_amount(
    payload: dict, era_grain_fids: frozenset[str],
) -> None:
    """ROADMAP #204 invariant at the build_lineage_flow call: no amount the
    /lineage/ payload chose is an era grain (spec 2026-10-02 §6.2 keeps era
    points off lineage). build_lineage_flow takes only the FY2026 request
    point (lineage.flow.AMOUNT_FY), which no PB2017-PB2023 grain can be;
    this check stops that from resting on one constant in another module."""
    from govbudget.lineage.flow import AMOUNT_FY

    chosen = {
        node["amount"]["fid"]
        for group in [*payload.get("families", []), *payload.get("candidates", [])]
        for node in group.get("nodes", [])
        if isinstance(node.get("amount"), dict)
    }
    leaked = sorted(chosen & era_grain_fids)
    if leaked:
        raise RuntimeError(
            f"lineage flow: {len(leaked)} FY{AMOUNT_FY} amount(s) chosen from an era grain"
            f" ({', '.join(leaked[:5])}); era points stay off /lineage/"
            " (spec 2026-10-02 §6.2, ROADMAP #204)"
        )


def _emit_lineage(
    *,
```

and replace:

```python
    lineage_flow_payload = build_lineage_flow(
        edges=_lin_edges,
        families=_lin_families,
        titles_by_pe=titles_by_pe,
        page_pes=all_pe_blis | set(rollup_pes) | set(decade_only_pes),
        decade_series_by_pe=decade_series_by_pe,
        cited_fact_ids=_cited_fact_ids,
    )
```

with:

```python
    lineage_flow_payload = build_lineage_flow(
        edges=_lin_edges,
        families=_lin_families,
        titles_by_pe=titles_by_pe,
        page_pes=all_pe_blis | set(rollup_pes) | set(decade_only_pes),
        decade_series_by_pe=decade_series_by_pe,
        cited_fact_ids=_cited_fact_ids,
    )
    # ROADMAP #204: era grains never reach /lineage/. Asserted here, at the
    # call, not only through build_lineage_flow's FY2026-only rule.
    _assert_lineage_flow_has_no_era_amount(lineage_flow_payload, era_grain_fids)
```

- [ ] **Step 3: Make the fence argument required**

Replace:

```python
    cited_fact_ids: set[str],
    era_grain_fids: frozenset[str] = frozenset(),
) -> dict[str, dict]:
```

with:

```python
    cited_fact_ids: set[str],
    era_grain_fids: frozenset[str],
) -> dict[str, dict]:
```

Replace:

```python
    era_grain_fids: frozenset[str] = frozenset(),
) -> int:
    """Emit all JSON sidecars to out_dir/json/.
```

with:

```python
    era_grain_fids: frozenset[str],
) -> int:
    """Emit all JSON sidecars to out_dir/json/.

    era_grain_fids is required (ROADMAP #204): a caller that forgot it would
    put era points on a fenced surface silently.
```

Replace:

```python
    era_grain_fids: frozenset[str] = frozenset(),
) -> int:
    """Core sidecar writer; called from _emit_json_sidecars.
```

with:

```python
    era_grain_fids: frozenset[str],
) -> int:
    """Core sidecar writer; called from _emit_json_sidecars.
```

Python allows a required keyword-only parameter after keyword-only parameters with defaults, so no other parameter moves.

- [ ] **Step 4: Update the two test callers that relied on the default**

In `tests/jbooks/test_export_lineage.py`, replace:

```python
        decade_series_by_pe=series,
        cited_fact_ids=set(cited),
    )
```

with:

```python
        decade_series_by_pe=series,
        cited_fact_ids=set(cited),
        era_grain_fids=frozenset(),
    )
```

In `tests/test_program_member_enrichment.py`, replace:

```python
    _emit_json_sidecars(out_dir=out, duckdb_path=db, detail_rows=details,
                       bl_rows=bl_rows, citation_rows=citations, manifest={})
```

with:

```python
    _emit_json_sidecars(out_dir=out, duckdb_path=db, detail_rows=details,
                       bl_rows=bl_rows, citation_rows=citations, manifest={},
                       era_grain_fids=frozenset())
```

- [ ] **Step 5: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_era_fences_required.py tests/jbooks/test_export_lineage.py tests/test_program_member_enrichment.py tests/test_export_decade_era_map.py tests/jbooks/test_export_site_pg.py -q 2>&1 | tail -1
uv run --project . python - <<'EOF'
import ast, pathlib
names = {"_emit_lineage", "_emit_json_sidecars", "_write_all_sidecars"}
calls = missing = 0
for root in ("src", "tests", "scripts"):
    for path in sorted(pathlib.Path(root).rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                if name in names:
                    calls += 1
                    if not any(k.arg == "era_grain_fids" for k in node.keywords):
                        missing += 1
                        print(f"{path}:{node.lineno} omits era_grain_fids")
print(f"{calls} calls, {missing} without era_grain_fids")
EOF
uvx --offline ruff check --isolated --select F,E9 src/govbudget/export_site.py | grep '^Found'
```

Expected: pytest ends `passed` with no failure — on 2026-10-13 HEAD with Task 13's fence removal simulated in a scratch copy, these five files gave `95 passed`; Task 13's own new or changed tests in them shift that count, never the outcome. Then `6 calls, 0 without era_grain_fids` (three in `export_site.py`, two in `tests/jbooks/test_export_lineage.py`, one in `tests/test_program_member_enrichment.py`). Then `Found 10 errors.` — the `export_site.py` HEAD baseline (spec §7 W1), so nothing new.

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/export_site.py GovBudget/tests/test_export_era_fences_required.py GovBudget/tests/jbooks/test_export_lineage.py GovBudget/tests/test_program_member_enrichment.py GovBudget/tests/jbooks/test_export_site_pg.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "refactor(export): era_grain_fids is required on the lineage and sidecar emitters; assert no era grain supplies a /lineage/ amount (#204)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `5 files changed`.
