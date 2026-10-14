<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21b: Release-1 proof tools — fact delta and the /years/ shard proof (P2b)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 P1 ("every A fact is unchanged except the named aggregates"), P2 ("`citations.json` must be identical"), P2b (`scripts/fu/years_shard_proof.py`: merge, `build_id`, every A cell in B, leg j's rule, the org-split rows, the counts and caps), §1 "Facts", §3.2–§3.6, §4.7 (the totals that move), Q11, Q15.

**Files:**
- Create: `scripts/fu/fact_delta.py`, `tests/test_fu_fact_delta.py`
- Create: `scripts/fu/years_shard_proof.py`, `tests/test_fu_years_shard_proof.py`

**Interfaces:**
Consumes:
- `scripts/era/fact_stability.py` `compare_citations(a: dict, b: dict, f15_leaves: dict[str, str], *, expected_f15: int, noise_classes: list[dict] | None) -> dict` with keys `missing` (list of fids), `changed` (list of `{"fact_id", "field", "a", "b"}`), `noise_equivalent`, `reorder_classes_trusted` — today's signature, which Task 2 keeps while it moves the module onto a public proof API. With `f15_leaves={}` and `expected_f15=0` it judges every field by proof diff's own noise rules and expects no F-15 restamp.
- `govbudget.proof.load_noise_classes(path) -> list[dict]` (public today).
- Task 13: `govbudget.export_site.split_years_matrix(payload: dict) -> dict[str, dict]` returning `{"years_matrix.json": core, "years_matrix/decade.json": …, "years_matrix/detail.json": …}` (paths relative to `json/`), `merge_years_matrix(core: dict, *shards: dict) -> dict` (its inverse up to `schema_version`, `build_id`, `shards` and each row's `np`; raises `ValueError` on a shard whose `build_id` differs from the core's), `_canonical_json_bytes(obj) -> bytes` (sorted keys, `(",", ":")`: the bytes the exporter writes), `_YEARS_MATRIX_MAX_BYTES` (4,194,304, unchanged) and `_YEARS_MATRIX_CORE_GZIP_MAX` (780,074). Every file carries the same 64-hex `build_id` (the sha256 of the canonical v1 payload); the core's `shards` is `[{name, path, columns, bytes, sha256}]` with `path` `years_matrix/decade.json` and `years_matrix/detail.json`; the shards are `{schema_version: 2, build_id, shard, columns, rows}`.
- A `govbudget proof diff --report FILE` file: `{"report": {"files": {rel: {"status", …}}, …}, "verdict": …}` (`src/govbudget/cli.py` `cmd_proof`).
Produces:
- `scripts/fu/fact_delta.py`: `explained_new(a, b, pe_bli: set[str]) -> tuple[set[str], list[str]]`; `judge_citations(a, b, *, expect: dict, noise_classes) -> dict`; `judge_rows(a_site, b_site, rel: str, allowed: list[str] | None) -> dict`; `judge_breakdowns(diff_report: dict, *, moved: set[str], new_in_b: set[str]) -> dict`; `run(a_site, b_site, *, expect, noise_from, diff_report) -> dict`; CLI `--a SITE --b SITE [--expect FILE] [--noise-from FILE] [--diff-report FILE] [--report FILE]`, last line `fact-delta: PASS|FAIL`; exit 0/1, tool error 2. The `--expect` object is `{"explained_by_pe_bli": [...], "moved": {fid: {"why", "delta_thousands"}}, "rows": {rel: [allowed pe_bli]}}` (Task 21c writes `expected-fact-moves-lake.json`).
- `scripts/fu/years_shard_proof.py`: `ORG_SPLIT_ROWS` (the seven #207 slugs); `run(a_site, b_site, *, merge=None, max_bytes=None, core_gzip_max=None) -> dict` with `sizes`, `build_id`, `rows`, `decade_cells_added` (`era`, `modern`, `era_default`, `modern_default`, `era_org_split`, `modern_org_split`), `org_split_nondecade_added`, `leg_j_mismatches`, `panel` (`a`/`b`: `programs`, `of`, `first_to_last_pct`, `fy2024a_to_fy2026r_pct`), `violations`; CLI `--a SITE --b SITE [--expect-era-added N] [--expect-modern-added N] [--report FILE]`, last line `years-shard-proof: PASS|FAIL`; exit 0/1, tool error 2.
- Used by Tasks 21f (P1, P2, P2b) and 22c (the release's wave citation delta comes from 21f's `p1-fact-delta.json`).

Measured for this task (2026-10-13, read-only on the live export `data/site`, built 2026-10-04T19:25:35Z):
- **fact_delta on the live export against itself:** `citations: A 143,841, B 143,841, new in B 0 {}, moved 0, …`, `data/budget_lines.parquet: A 8,549 rows`, `data/budget_lines_decade.parquet: A 56,264 rows`, `data/fct_budget_trajectory.parquet: A 1,988 rows`, `fact-delta: PASS`, in 1.8 s (`json/citations.json` is 95,386,479 bytes).
- **The aggregates the 0390DOM row moves.** The only derived citations whose inputs hold account 0390D's one FY2026 leaf (`1a042b451c36b00f`, R-1 0708083D, FY2026 total 210,039) are the universe fact `709cbd08c6b7dfb0` (`site_meta.programs_coverage.universe_fact_id`), ten flow-chart nodes and edges (`c216c55e0ddffec1` b:total, `d2f5b699e5123b11` b:c:A, `da3a508dbe8427f4` b:c:A→b:other:appropriation, `ce38e79987ed7a92` b:other:appropriation, `ac97b301729e8743`, `980c6bbee984f264`, `9a77d80916d1cead`, `ce27343e3d87e507`, `25e51edb9bfa36b3`, `6ca3c62f32d31298` bridge not-crosswalked), 0708083D's own sum `8c650c32344ce447` and its book diff `f0b176801437ee13`. All their inputs are `workbook` leaves (the flow total's 1,714 inputs are all workbook), every P-1 `fy_2026_total` is a workbook leaf (e.g. F015EX `03407158217dec76`, cell W847), and each of the eleven aggregates has a `json/breakdowns/<fid>.json`. So the 0390DOM FY2026 total leaf (3,243) moves exactly those eleven by +3,243, which is the rule `fact_delta` enforces with Task 21c's file. The design's §4.7 named five of them; the other six are the flow chart's "Other" nodes and edges on the same path.
- **P2b on a simulated B.** `years_shard_proof.run` with a stub merge, on A = the live `json/years_matrix.json` and B = the same payload with every decade cell its program sidecar implies added (the leg j rule, the design's `ym_era_sim.py` method), reads `PASS` with `decade_cells_added` `{"era": 14985, "modern": 63, "era_default": 4995, "modern_default": 35, "era_org_split": 147, "modern_org_split": 63}`, `leg_j_mismatches 0`, and the totals chart's balanced panel A `524 of 1,938`, FY2024A→FY2026R `9.34`%, first→last `108.17`%, B `1,063 of 1,938`, `-2.61`%, `103.71`%. 14,985 and 4,995 reproduce the design's §3.1 counts; the 63 modern and 147 era org-split cells reproduce §3.5. The B panel is 1,063, not the design's Q15 figure of 1,056: the seven org-split rows (#207), which the design's simulation left without cells, reach the panel once Task 13 fixes `_acct_key` (1,063 − 1,056 = 7). Task 22d names both numbers in the owner's go-ahead.
- **Against Task 13's code.** With `split_years_matrix`, `merge_years_matrix`, `_canonical_json_bytes` and `years_matrix_row_key` taken verbatim from `13-years-exporter-split.md` (lines 1051–1218) and injected into `govbudget.export_site`, the six tests below pass, and the same simulated B, split by that code and written with `_canonical_json_bytes`, reads `PASS` with sizes `years_matrix.json` 1,100,823 / 344,303 gzip, `years_matrix/decade.json` 1,390,739 / 433,932, `years_matrix/detail.json` 1,231,643 / 284,230 — Task 13's own simulation, to the byte (this tool's `gzip.compress(…, compresslevel=9, mtime=0)` agrees with it).

- [ ] **Step 1: Write the failing fact-delta tests**

Create `tests/test_fu_fact_delta.py`:

```python
"""scripts/fu/fact_delta.py — fact-level judgement of an A/B pair (follow-ups Task 21b)."""
import copy
import json

import duckdb

from fu.fact_delta import explained_new, judge_breakdowns, judge_citations, main  # scripts/ is on sys.path

TOTAL, OTHER = "c216c55e0ddffec1", "5d7f4f6d5b68de15"
R1, NEW, NEW2, ERA = "1a042b451c36b00f", "aaaaaaaaaaaaaaa1", "aaaaaaaaaaaaaaa2", "bbbbbbbbbbbbbbb1"


def wb(pe_bli, amount):
    return {"kind": "workbook", "pe_bli": pe_bli, "amount_thousands": amount, "units": "USD thousands",
            "retrieved_at": "2026-06-10T16:08:15.770221-04:00", "sha256": "f" * 64, "cells": "P241"}


def dv(inputs, value, stamp="2026-10-04T19:25:15.827166+00:00"):
    return {"kind": "derived", "inputs": json.dumps(inputs), "recorded_value": value, "retrieved_at": stamp,
            "formula": "sum(budget_lines.amount_thousands where amount_type=fy_2026_total and flow_node=b:total)",
            "units": "USD thousands", "pe_bli": None}


def a_side():
    return {R1: wb("0708083D", 210039.0), TOTAL: dv([R1], "210039.000"), OTHER: dv([R1], "210039.000")}


def b_side():
    b = copy.deepcopy(a_side())
    b[NEW] = wb("0390DOM", 3243.0)
    b[NEW2] = wb("0390DOM", 87404.0)
    b[ERA] = dv([NEW2], "87404.000")
    b[TOTAL] = dv([R1, NEW], "213282.000", stamp="2026-10-14T01:00:00+00:00")
    b[OTHER] = dv([R1, NEW], "213282.000")
    return b


EXPECT = {"explained_by_pe_bli": ["0390DOM"],
          "moved": {TOTAL: {"why": "flow total", "delta_thousands": "3243.000"},
                    OTHER: {"why": "other appropriations", "delta_thousands": "3243.000"}}}


def test_named_aggregates_may_gain_explained_inputs_by_exactly_their_amount():
    report = judge_citations(a_side(), b_side(), expect=EXPECT, noise_classes=None)
    assert report["ok"], report["violations"]
    assert sorted(report["moved"]) == sorted([TOTAL, OTHER])
    assert report["moved"][TOTAL] == {"added_inputs": [NEW], "delta_thousands": "3243.000",
                                      "a": "210039.000", "b": "213282.000"}
    assert report["new_in_b"] == 3 and report["new_by_kind"] == {"derived": 1, "workbook": 2}


def test_new_facts_must_trace_to_the_explained_code():
    a, b = a_side(), b_side()
    b["ccccccccccccccc1"] = wb("0708081D", 1.0)
    b["ccccccccccccccc2"] = dv(["ccccccccccccccc1"], "1.000")
    explained, unexplained = explained_new(a, b, {"0390DOM"})
    assert explained == {NEW, NEW2, ERA}
    assert unexplained == ["ccccccccccccccc1", "ccccccccccccccc2"]
    assert not judge_citations(a, b, expect=EXPECT, noise_classes=None)["ok"]


def test_a_move_that_is_not_named_or_not_exact_fails():
    b = b_side()
    b[OTHER] = dv([R1, NEW], "213283.000")
    report = judge_citations(a_side(), b, expect=EXPECT, noise_classes=None)
    assert any("recorded_value moved 3244.000" in v for v in report["violations"])
    unnamed = {**EXPECT, "moved": {TOTAL: EXPECT["moved"][TOTAL]}}
    report = judge_citations(a_side(), b_side(), expect=unnamed, noise_classes=None)
    assert f"changed outside the expected moves: {OTHER} (inputs, recorded_value)" in report["violations"]


def test_a_named_move_that_did_not_happen_fails_and_so_does_a_dropped_input():
    b = b_side()
    b[OTHER] = copy.deepcopy(a_side()[OTHER])
    report = judge_citations(a_side(), b, expect=EXPECT, noise_classes=None)
    assert f"expected move did not happen: {OTHER} (other appropriations)" in report["violations"]
    b = b_side()
    b[TOTAL] = dv([NEW], "3243.000")
    report = judge_citations(a_side(), b, expect=EXPECT, noise_classes=None)
    assert any(v.startswith(f"moved fact {TOTAL} dropped inputs") for v in report["violations"])


def test_without_expectations_nothing_may_move_or_appear_but_run_stamps_may():
    b = copy.deepcopy(a_side())
    b[TOTAL]["retrieved_at"] = "2026-10-14T01:00:00+00:00"
    assert judge_citations(a_side(), b, expect={}, noise_classes=None)["ok"]
    assert not judge_citations(a_side(), b_side(), expect={}, noise_classes=None)["ok"]
    gone = a_side()
    del gone[R1]
    assert "missing in B: " + R1 in judge_citations(a_side(), gone, expect={}, noise_classes=None)["violations"]


def test_breakdowns_change_only_for_moved_facts():
    files = {f"json/breakdowns/{TOTAL}.json": {"status": "changed"},
             f"json/breakdowns/{ERA}.json": {"status": "only_b"},
             "json/breakdowns/0000000000000001.json": {"status": "equivalent"}}
    assert judge_breakdowns({"report": {"files": files}}, moved={TOTAL}, new_in_b={ERA})["ok"]
    files["json/breakdowns/0000000000000002.json"] = {"status": "only_a"}
    assert judge_breakdowns({"report": {"files": files}}, moved={TOTAL}, new_in_b={ERA})["violations"] == [
        "breakdown 0000000000000002: only_a"]


def write_site(root, citations, rows):
    (root / "json").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "json" / "citations.json").write_text(json.dumps(citations))
    con = duckdb.connect()
    for name, data in rows.items():
        con.execute("create or replace table t (fact_id varchar, pe_bli varchar, amount_thousands double)")
        if data:
            con.executemany("insert into t values (?, ?, ?)", data)
        con.execute(f"copy t to '{root / 'data' / name}' (format parquet)")
    con.close()
    return root


ROWS_A = {"budget_lines.parquet": [(R1, "0708083D", 210039.0)],
          "budget_lines_decade.parquet": [(R1, "0708083D", 210039.0)],
          "fct_budget_trajectory.parquet": [(None, "0708083D", 210039.0)]}


def test_cli_rows_and_verdicts(tmp_path, capsys):
    rows_b = copy.deepcopy(ROWS_A)
    rows_b["budget_lines.parquet"].append((NEW, "0390DOM", 3243.0))
    rows_b["budget_lines_decade.parquet"] += [(NEW, "0390DOM", 3243.0), (ERA, "0390D-ARMY-L1", 87404.0)]
    a = write_site(tmp_path / "a", a_side(), ROWS_A)
    b = write_site(tmp_path / "b", b_side(), rows_b)
    expect = {**EXPECT, "rows": {"data/budget_lines.parquet": ["0390DOM"],
                                 "data/budget_lines_decade.parquet": ["0390DOM", "0390D-ARMY-L1"],
                                 "data/fct_budget_trajectory.parquet": ["0390DOM"]}}
    (tmp_path / "expect.json").write_text(json.dumps(expect))
    assert main(["--a", str(a), "--b", str(b), "--expect", str(tmp_path / "expect.json"),
                 "--report", str(tmp_path / "r.json")]) == 0
    out = capsys.readouterr().out
    assert out.strip().endswith("fact-delta: PASS")
    assert 'data/budget_lines_decade.parquet: A 1 rows, B 3, A rows not in B 0, B-only rows by pe_bli ' \
           '{"0390D-ARMY-L1": 1, "0390DOM": 1}' in out
    assert main(["--a", str(a), "--b", str(b)]) == 1          # without --expect nothing may move
    assert main(["--a", str(a), "--b", str(a)]) == 0          # identical trees
    assert main(["--a", str(a), "--b", str(tmp_path / "nope")]) == 2
    assert "fact-delta: ERROR — " in capsys.readouterr().err
```

- [ ] **Step 2: Write the failing shard-proof tests**

Create `tests/test_fu_years_shard_proof.py`:

```python
"""scripts/fu/years_shard_proof.py — P2b, the /years/ shard proof (follow-ups Task 21b)."""
import copy
import json

from fu.years_shard_proof import main, run  # scripts/ is on sys.path

BUILD = "b" * 64
COLS = [{"edition": 2017, "fy": 2015, "key": "fy2015a", "kind": "actuals", "measures": ["actuals-base-oco"]},
        {"edition": 2026, "fy": 2024, "key": "fy2024a", "kind": "actuals", "measures": ["actuals"]},
        {"edition": 2026, "fy": 2026, "key": "fy2026r", "kind": "request"}]


def cell(fid, v):
    return {"fid": fid, "v": v}


def point(kind, edition, fy, fid, v):
    return {"basis": "toa", "edition": edition, "fid": fid, "fy": fy, "measure": kind, "v": v}


def v1(rows_by_org):
    return {"amount_types": ["fy_2024_actuals", "fy_2025_total", "fy_2026_total"],
            "decade_columns": COLS, "decade_default_columns": ["fy2015a", "fy2024a", "fy2026r"],
            "default_columns": ["fy_2024_actuals", "fy_2026_total"], "delta_columns": ["fy2526_change"],
            "orgs": [{"org": org, "programs": rows} for org, rows in rows_by_org.items()],
            "program_units": "USD thousands", "project_scenarios": {}, "project_units": "USD millions",
            "schema_version": 1}


R1 = {"pe_bli": "0207134F", "title": "F-15E Squadrons", "projects": [],
      "cells": {"fy2015a": cell("1000000000000001", 10.0), "fy2024a": cell("1000000000000002", 20.0),
                "fy2026r": cell("1000000000000003", 30.0)}}
P1 = {"pe_bli": "F01500", "title": "F-15", "projects": [],
      "cells": {"fy2024a": cell("2000000000000002", 5.0), "fy2026r": cell("2000000000000003", 4.0)}}
SPLIT = {"pe_bli": "20", "slug": "20-DCSA", "title": "Major Equipment", "projects": [],
         "cells": {"fy_2024_actuals": cell("3000000000000009", 2135.0)}}
SIDECARS = {
    "0207134F": {"actuals": [point("actuals", 2017, 2015, "1000000000000001", 10.0),
                             point("actuals", 2026, 2024, "1000000000000002", 20.0)],
                 "request": [point("request", 2026, 2026, "1000000000000003", 30.0)]},
    "F01500": {"actuals": [point("actuals", 2017, 2015, "2000000000000001", 498314.0),
                           point("actuals", 2026, 2024, "2000000000000002", 5.0)],
               "request": [point("request", 2026, 2026, "2000000000000003", 4.0)]},
    "20-DCSA": {"actuals": [point("actuals", 2017, 2015, "3000000000000001", 1.0),
                            point("actuals", 2026, 2024, "3000000000000002", 2135.0)]},
}


def a_payload():
    return v1({"AF": [copy.deepcopy(R1), copy.deepcopy(P1)], "DCSA": [copy.deepcopy(SPLIT)]})


def b_payload():
    p = a_payload()
    af, dcsa = p["orgs"][0]["programs"], p["orgs"][1]["programs"]
    af[1]["cells"]["fy2015a"] = cell("2000000000000001", 498314.0)          # era cell, fence lifted
    dcsa[0]["cells"]["fy2015a"] = cell("3000000000000001", 1.0)            # org-split row: era cell
    dcsa[0]["cells"]["fy2024a"] = cell("3000000000000002", 2135.0)         # org-split row: modern cell
    dcsa[0]["cells"]["fy_2025_total"] = cell("3000000000000010", 2191.0)   # org-split row: amount type
    return p


def stub_merge(core, decade, detail):
    merged = {k: v for k, v in core.items() if k not in ("build_id", "shards")}
    merged["schema_version"] = 1
    return merged


def write(root, a=None, b=None, *, ids=(BUILD, BUILD, BUILD)):
    (root / "json" / "years_matrix").mkdir(parents=True)
    (root / "json" / "program_details").mkdir()
    if a is not None:
        (root / "json" / "years_matrix.json").write_text(json.dumps(a))
    if b is not None:
        core = {**b, "schema_version": 2, "build_id": ids[0]}
        (root / "json" / "years_matrix.json").write_text(json.dumps(core))
        (root / "json" / "years_matrix" / "decade.json").write_text(json.dumps({"build_id": ids[1]}))
        (root / "json" / "years_matrix" / "detail.json").write_text(json.dumps({"build_id": ids[2]}))
    for slug, series in SIDECARS.items():
        (root / "json" / "program_details" / f"{slug}.json").write_text(json.dumps({"decade_series": series}))
    return root


def proof(tmp_path, b, **kw):
    a_site = write(tmp_path / "a", a=a_payload())
    b_site = write(tmp_path / "b", b=b, **kw)
    return run(a_site, b_site, merge=stub_merge, max_bytes=4 * 1024 * 1024, core_gzip_max=780_074)


def test_lifted_fence_and_org_split_fix_pass_and_are_counted(tmp_path):
    report = proof(tmp_path, b_payload())
    assert report["ok"], report["violations"]
    assert report["decade_cells_added"] == {"era": 2, "modern": 1, "era_default": 2, "modern_default": 1,
                                            "era_org_split": 1, "modern_org_split": 1}
    assert report["org_split_nondecade_added"] == {"20-DCSA": ["fy_2025_total"]}
    assert report["panel"]["a"]["programs"] == 1 and report["panel"]["b"]["programs"] == 2
    assert report["panel"]["b"]["fy2024a_to_fy2026r_pct"] == round(100 * (34.0 - 25.0) / 25.0, 2)


def test_a_cell_the_sidecar_lacks_or_a_missing_cell_fails_leg_j(tmp_path):
    b = b_payload()
    b["orgs"][0]["programs"][0]["cells"]["fy2026r"] = cell("1000000000000099", 30.0)
    report = proof(tmp_path, b)
    assert any("leg j fy2026r" in v for v in report["violations"]) and report["leg_j_mismatches"] == 1
    b = b_payload()
    del b["orgs"][0]["programs"][1]["cells"]["fy2015a"]
    assert proof(tmp_path / "2", b)["leg_j_mismatches"] == 1


def test_a_changed_a_cell_and_a_stray_non_decade_cell_fail(tmp_path):
    b = b_payload()
    b["orgs"][0]["programs"][1]["cells"]["fy2024a"] = cell("2000000000000002", 6.0)
    assert any("A cell fy2024a changed" in v for v in proof(tmp_path, b)["violations"])
    b = b_payload()
    b["orgs"][0]["programs"][1]["cells"]["fy_2025_total"] = cell("2000000000000010", 1.0)
    assert "F01500: B adds non-decade cells ['fy_2025_total']" in proof(tmp_path / "2", b)["violations"]


def test_build_ids_must_agree_and_caps_hold(tmp_path):
    report = proof(tmp_path, b_payload(), ids=(BUILD, BUILD, "c" * 64))
    assert any(v.startswith("build_id differs") for v in report["violations"])
    a_site = write(tmp_path / "x" / "a", a=a_payload())
    b_site = write(tmp_path / "x" / "b", b=b_payload())
    report = run(a_site, b_site, merge=stub_merge, max_bytes=100, core_gzip_max=10)
    assert any("over the 100-byte cap" in v for v in report["violations"])
    assert any("gzip bytes, over 10" in v for v in report["violations"])


def test_the_real_split_round_trips_through_the_proof(tmp_path):
    """Task 13's split_years_matrix and merge_years_matrix, end to end: B = split(A) adds nothing."""
    from govbudget.export_site import _canonical_json_bytes, split_years_matrix

    payload = a_payload()
    a_site = write(tmp_path / "a", a=payload)
    b_site = tmp_path / "b"
    (b_site / "json" / "program_details").mkdir(parents=True)
    for rel, obj in split_years_matrix(copy.deepcopy(payload)).items():
        (b_site / "json" / rel).parent.mkdir(parents=True, exist_ok=True)
        (b_site / "json" / rel).write_bytes(_canonical_json_bytes(obj))
    for slug, series in SIDECARS.items():
        (b_site / "json" / "program_details" / f"{slug}.json").write_text(json.dumps({"decade_series": series}))
    report = run(a_site, b_site)
    # F01500's and 20-DCSA's sidecar points have no cell in A, so leg j counts them: exactly those three.
    assert report["leg_j_mismatches"] == 3, report["violations"]
    assert report["decade_cells_added"]["era"] == 0 and report["rows"] == {"a": 3, "b": 3}
    assert not [v for v in report["violations"] if "build_id" in v or "shard manifest" in v or "header" in v]


def test_cli(tmp_path, capsys):
    a_site = write(tmp_path / "a", a=a_payload())
    write(tmp_path / "b", b=b_payload())
    assert main(["--a", str(a_site), "--b", str(tmp_path / "nope")]) == 2
    assert "years-shard-proof: ERROR — " in capsys.readouterr().err
```

- [ ] **Step 3: Run both files to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_fu_fact_delta.py tests/test_fu_years_shard_proof.py -q`
Expected: two collection errors, `ModuleNotFoundError: No module named 'fu.fact_delta'` and `ModuleNotFoundError: No module named 'fu.years_shard_proof'` (Task 21a created `scripts/fu/`).

- [ ] **Step 4: Implement `scripts/fu/fact_delta.py`**

```python
#!/usr/bin/env python3
"""Fact-level judgement of an A/B pair of data/site trees (families piece-1
follow-ups, Task 21b; design §7 P1 and P2, §1 "Facts", §4.7).

`govbudget proof diff` judges files and JSON pointers; this judges facts.

  * Every fact A publishes is in B. A fact in both may differ only by export
    noise and run stamps (judged by era.fact_stability.compare_citations,
    which applies proof diff's own rules, with no F-15 restamp expected), or —
    when an --expect file names it under "moved" — as a derived aggregate
    that GAINED inputs: B's inputs are A's plus k facts, each new in B and
    explained (below), no input is dropped, only `inputs` and
    `recorded_value` change, and recorded_value moved by exactly the summed
    amount of the added inputs, which must equal the expected delta. A named
    aggregate that did not move is a failure too.
  * Every fact new in B is explained: a workbook citation whose pe_bli is in
    "explained_by_pe_bli", or a derived citation every input of which is an
    explained fact new in B. Without --expect, B may add no fact at all.
  * Every row of each named site parquet in A is a row of B (EXCEPT ALL,
    every column), and each row only B has carries a pe_bli in that
    dataset's allowed list. Without --expect the datasets compare equal both
    ways: data/budget_lines.parquet, data/budget_lines_decade.parquet and
    data/fct_budget_trajectory.parquet.
  * With --diff-report (a `proof diff --report` file for the same pair): a
    breakdown file json/breakdowns/<fid>.json changed only for a moved fact,
    exists only in B only for a fact new in B, and never exists only in A.

--expect is a JSON object:
  {"explained_by_pe_bli": ["0390DOM"],
   "moved": {"<fid>": {"why": "...", "delta_thousands": "3243.000"}, ...},
   "rows": {"data/budget_lines.parquet": ["0390DOM"], ...}}

Last line `fact-delta: PASS|FAIL`; exit 0/1; a tool error prints
`fact-delta: ERROR — <message>` and exits 2.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/, for era.fact_stability when run directly
from era.fact_stability import compare_citations  # noqa: E402

DEFAULT_ROWS = ("data/budget_lines.parquet", "data/budget_lines_decade.parquet",
                "data/fct_budget_trajectory.parquet")
MOVABLE_FIELDS = frozenset({"inputs", "recorded_value"})
SHOW = 20


def _inputs(citation: dict) -> list[str]:
    raw = citation.get("inputs")
    value = json.loads(raw) if isinstance(raw, str) else raw
    return [item for item in value or [] if isinstance(item, str)]


def _amount(citation: dict) -> Decimal:
    if citation.get("kind") == "workbook":
        return Decimal(str(citation["amount_thousands"]))
    return Decimal(str(citation["recorded_value"]))


def explained_new(a: dict, b: dict, pe_bli: set[str]) -> tuple[set[str], list[str]]:
    """(explained, unexplained) facts new in B."""
    new = set(b) - set(a)
    explained = {fid for fid in new if b[fid].get("kind") == "workbook" and b[fid].get("pe_bli") in pe_bli}
    grew = True
    while grew:
        grew = False
        for fid in sorted(new - explained):
            if b[fid].get("kind") != "derived":
                continue
            ins = _inputs(b[fid])
            if ins and all(i in explained for i in ins):
                explained.add(fid)
                grew = True
    return explained, sorted(new - explained)


def judge_citations(a: dict, b: dict, *, expect: dict, noise_classes: list[dict] | None) -> dict:
    base = compare_citations(a, b, {}, expected_f15=0, noise_classes=noise_classes)
    pe_bli = set(expect.get("explained_by_pe_bli", []))
    moved_expected: dict = expect.get("moved", {})
    explained, unexplained = explained_new(a, b, pe_bli)
    violations = [f"missing in B: {fid}" for fid in base["missing"]]
    violations += [f"new in B and not explained by {sorted(pe_bli) or 'nothing'}: {fid} ({b[fid].get('kind')})"
                   for fid in unexplained]
    changed: dict[str, set[str]] = {}
    for item in base["changed"]:
        changed.setdefault(item["fact_id"], set()).add(item["field"])
    moved = {}
    for fid, fields in sorted(changed.items()):
        if fid not in moved_expected:
            violations.append(f"changed outside the expected moves: {fid} ({', '.join(sorted(fields))})")
            continue
        ca, cb = a[fid], b[fid]
        if ca.get("kind") != "derived" or cb.get("kind") != "derived":
            violations.append(f"moved fact {fid} is not a derived aggregate on both sides")
            continue
        if not fields <= MOVABLE_FIELDS:
            violations.append(f"moved fact {fid} changed {sorted(fields - MOVABLE_FIELDS)} (only inputs/recorded_value may)")
            continue
        ins_a, ins_b = _inputs(ca), _inputs(cb)
        dropped = sorted(set(ins_a) - set(ins_b))
        added = sorted(set(ins_b) - set(ins_a))
        if dropped:
            violations.append(f"moved fact {fid} dropped inputs {dropped[:5]}")
            continue
        if not added or any(i not in explained for i in added):
            violations.append(f"moved fact {fid} gained inputs that are not explained new facts: {added[:5]}")
            continue
        delta = Decimal(cb["recorded_value"]) - Decimal(ca["recorded_value"])
        summed = sum((_amount(b[i]) for i in added), Decimal(0))
        want = Decimal(moved_expected[fid]["delta_thousands"])
        if delta != summed or delta != want:
            violations.append(f"moved fact {fid}: recorded_value moved {delta}, added inputs sum {summed}, expected {want}")
            continue
        moved[fid] = {"added_inputs": added, "delta_thousands": str(delta),
                      "a": ca["recorded_value"], "b": cb["recorded_value"]}
    for fid in sorted(set(moved_expected) - set(changed)):
        violations.append(f"expected move did not happen: {fid} ({moved_expected[fid].get('why', '')})")
    new_kinds: dict[str, int] = {}
    for fid in set(b) - set(a):
        new_kinds[b[fid].get("kind")] = new_kinds.get(b[fid].get("kind"), 0) + 1
    return {"ok": not violations, "a_facts": len(a), "b_facts": len(b), "new_in_b": len(set(b) - set(a)),
            "new_by_kind": dict(sorted(new_kinds.items())), "moved": moved,
            "noise_equivalent": base["noise_equivalent"],
            "reorder_classes_trusted": base["reorder_classes_trusted"], "violations": violations}


def judge_rows(a_site: Path, b_site: Path, rel: str, allowed: list[str] | None) -> dict:
    import duckdb

    pa, pb = Path(a_site) / rel, Path(b_site) / rel
    con = duckdb.connect()
    try:
        a, b = f"read_parquet('{pa.as_posix()}')", f"read_parquet('{pb.as_posix()}')"
        schema_a = [r[:2] for r in con.execute(f"describe select * from {a}").fetchall()]
        schema_b = [r[:2] for r in con.execute(f"describe select * from {b}").fetchall()]
        if schema_a != schema_b:
            return {"ok": False, "violations": [f"{rel}: schema differs"]}
        rows_a = con.execute(f"select count(*) from {a}").fetchone()[0]
        rows_b = con.execute(f"select count(*) from {b}").fetchone()[0]
        lost = con.execute(f"select count(*) from (select * from {a} except all select * from {b})").fetchone()[0]
        added = con.execute(f"select pe_bli, count(*) from (select * from {b} except all select * from {a})"
                            " group by pe_bli order by pe_bli").fetchall()
    finally:
        con.close()
    violations = [f"{rel}: {lost} row(s) of A are not in B"] if lost else []
    allowed_set = set(allowed or [])
    bad = [(p, n) for p, n in added if p not in allowed_set]
    if bad:
        violations.append(f"{rel}: rows only in B with pe_bli outside {sorted(allowed_set)}: {bad[:SHOW]}")
    return {"ok": not violations, "rows_a": rows_a, "rows_b": rows_b, "lost": lost,
            "added_by_pe_bli": {p: n for p, n in added}, "violations": violations}


def judge_breakdowns(diff_report: dict, *, moved: set[str], new_in_b: set[str]) -> dict:
    files = diff_report["report"]["files"]
    violations = []
    counts = {"changed": 0, "only_b": 0}
    for rel, entry in sorted(files.items()):
        if not rel.startswith("json/breakdowns/"):
            continue
        fid = rel[len("json/breakdowns/"):-len(".json")]
        status = entry["status"]
        if status in ("identical", "equivalent", "reordered"):
            continue
        if status == "changed" and fid in moved:
            counts["changed"] += 1
        elif status == "only_b" and fid in new_in_b:
            counts["only_b"] += 1
        else:
            violations.append(f"breakdown {fid}: {status}")
    return {"ok": not violations, **counts, "violations": violations}


def run(a_site: Path, b_site: Path, *, expect: dict | None, noise_from: Path | None,
        diff_report: Path | None) -> dict:
    from govbudget.proof import load_noise_classes

    a_site, b_site = Path(a_site), Path(b_site)
    expect = expect or {}
    a = json.loads((a_site / "json" / "citations.json").read_text())
    b = json.loads((b_site / "json" / "citations.json").read_text())
    classes = load_noise_classes(noise_from) if noise_from else None
    citations = judge_citations(a, b, expect=expect, noise_classes=classes)
    rows_spec = expect.get("rows") or {rel: [] for rel in DEFAULT_ROWS}
    rows = {rel: judge_rows(a_site, b_site, rel, allowed) for rel, allowed in sorted(rows_spec.items())}
    report = {"citations": citations, "rows": rows, "breakdowns": None}
    if diff_report is not None:
        report["breakdowns"] = judge_breakdowns(json.loads(Path(diff_report).read_text()),
                                                moved=set(citations["moved"]), new_in_b=set(b) - set(a))
    parts = [citations, *rows.values()] + ([report["breakdowns"]] if report["breakdowns"] else [])
    report["ok"] = all(part["ok"] for part in parts)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fact-level judgement of two data/site trees")
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--b", type=Path, required=True)
    p.add_argument("--expect", type=Path, default=None, help="explained pe_bli, moved aggregates, row rules")
    p.add_argument("--noise-from", type=Path, default=None, help="a `proof diff --control --write-noise` file")
    p.add_argument("--diff-report", type=Path, default=None, help="the `proof diff --report` file for this pair")
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        expect = json.loads(args.expect.read_text()) if args.expect else None
        report = run(args.a, args.b, expect=expect, noise_from=args.noise_from, diff_report=args.diff_report)
    except Exception as e:  # noqa: BLE001 — a tool error is exit 2, never a verdict
        print(f"fact-delta: ERROR — {e}", file=sys.stderr)
        return 2
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    c = report["citations"]
    print(f"citations: A {c['a_facts']:,}, B {c['b_facts']:,}, new in B {c['new_in_b']:,} "
          f"{json.dumps(c['new_by_kind'], sort_keys=True)}, moved {len(c['moved'])}, "
          f"noise-equivalent fields {sum(c['noise_equivalent'].values()):,}")
    for fid, m in c["moved"].items():
        print(f"  moved {fid}: {m['a']} -> {m['b']} (+{m['delta_thousands']}, inputs +{len(m['added_inputs'])})")
    for rel, r in report["rows"].items():
        if "rows_a" in r:
            print(f"{rel}: A {r['rows_a']:,} rows, B {r['rows_b']:,}, A rows not in B {r['lost']:,}, "
                  f"B-only rows by pe_bli {json.dumps(r['added_by_pe_bli'], sort_keys=True)}")
    if report["breakdowns"]:
        bd = report["breakdowns"]
        print(f"breakdowns: changed {bd['changed']} (moved facts), only in B {bd['only_b']} (new facts)")
    violations = c["violations"] + [v for r in report["rows"].values() for v in r["violations"]]
    violations += report["breakdowns"]["violations"] if report["breakdowns"] else []
    for v in violations[:SHOW]:
        print(f"  violation: {v}")
    if len(violations) > SHOW:
        print(f"  ... and {len(violations) - SHOW} more violation(s) (see --report)")
    print(f"fact-delta: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `scripts/fu/years_shard_proof.py`**

```python
#!/usr/bin/env python3
"""P2b: the /years/ shard proof (families piece-1 follow-ups, Task 21b; design
§3.2-§3.6, §7 P2b, Q11, Q15).

A is a data/site tree exported by the deployed code (one schema-1
json/years_matrix.json); B is a tree exported by the follow-ups code from the
SAME snapshot (a schema-2 core json/years_matrix.json plus the lazy
json/years_matrix/decade.json and json/years_matrix/detail.json). The proof:

  1. B's three files carry one 64-hex build_id; when the core lists its
     shards (a list of {"path", "bytes", "sha256", ...}), each listed file
     has exactly those bytes and that sha256.
  2. B merged (govbudget.export_site.merge_years_matrix, the inverse of
     split_years_matrix) has A's header (every top-level key A has, except
     schema_version) and A's rows, keyed (org, slug or pe_bli).
  3. Every A cell is in B with the same fid and value.
  4. Non-decade cells are identical, except on the seven org-split rows
     (ORG_SPLIT_ROWS, ROADMAP #207), where B may add amount-type or delta
     cells (reported).
  5. Leg j: for every B row and every decade column, a cell is present if and
     only if the row's program sidecar json/program_details/<slug or
     pe_bli>.json has a decade_series point with the same (kind, edition, fy),
     and the cell's fid and value equal the point's.
  6. Every file is at most MAX_BYTES on disk, and the core is at most
     CORE_GZIP_MAX bytes at gzip level 9 (the exporter's own constants).

It reports the decade cells B adds (era = edition <= 2023, modern; default
view; the org-split rows) and the totals chart's balanced panel for A and B
(rows with a value in every default decade column; FY2024A->FY2026R and
first->last change), and compares the added counts with --expect-* when given.

Last line `years-shard-proof: PASS|FAIL`; exit 0/1; a tool error prints
`years-shard-proof: ERROR — <message>` and exits 2.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ORG_SPLIT_ROWS = frozenset({"20-DCSA", "20-DTRA", "30-DMACT", "30-DTRA", "30-OSD", "500-DHRA", "500-DLA"})
ERA_LAST_EDITION = 2023
ROW_META = frozenset({"cells", "np"})
_HEX64 = re.compile(r"[0-9a-f]{64}")
CORE, DECADE, DETAIL = "years_matrix.json", "years_matrix/decade.json", "years_matrix/detail.json"
SHOW = 20


def _load(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    return json.loads(data), data


def _rows(payload: dict) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for org in payload["orgs"]:
        for row in org["programs"]:
            key = (org["org"], row.get("slug") or row["pe_bli"])
            if key in out:
                raise ValueError(f"duplicate row key {key}")
            out[key] = row
    return out


def _panel(payload: dict, rows: dict) -> dict:
    meta = {c["key"]: c for c in payload["decade_columns"]}
    keys = payload["decade_default_columns"]
    panel = [r for r in rows.values() if all(r["cells"].get(k) is not None for k in keys)]
    sums = {k: sum(r["cells"][k]["v"] for r in panel) for k in keys}
    ordered = sorted(keys, key=lambda k: meta[k]["fy"])

    def pct(x, y):
        return round(100 * (sums[y] - sums[x]) / sums[x], 2) if sums.get(x) else None

    return {"programs": len(panel), "of": len(rows),
            "first_to_last_pct": pct(ordered[0], ordered[-1]),
            "fy2024a_to_fy2026r_pct": pct("fy2024a", "fy2026r") if {"fy2024a", "fy2026r"} <= set(keys) else None}


def run(a_site: Path, b_site: Path, *, merge=None, max_bytes: int | None = None,
        core_gzip_max: int | None = None) -> dict:
    if merge is None or max_bytes is None or core_gzip_max is None:
        from govbudget import export_site
        merge = merge or export_site.merge_years_matrix
        max_bytes = max_bytes or export_site._YEARS_MATRIX_MAX_BYTES
        core_gzip_max = core_gzip_max or export_site._YEARS_MATRIX_CORE_GZIP_MAX
    a_json, b_json = Path(a_site) / "json", Path(b_site) / "json"
    violations: list[str] = []

    a_payload, _ = _load(a_json / CORE)
    files = {name: _load(b_json / name) for name in (CORE, DECADE, DETAIL)}
    core, decade, detail = (files[n][0] for n in (CORE, DECADE, DETAIL))
    sizes = {}
    for name, (_, data) in files.items():
        gz = len(gzip.compress(data, compresslevel=9, mtime=0))
        sizes[name] = {"bytes": len(data), "gzip": gz}
        if len(data) > max_bytes:
            violations.append(f"{name}: {len(data):,} bytes, over the {max_bytes:,}-byte cap")
    if sizes[CORE]["gzip"] > core_gzip_max:
        violations.append(f"{CORE}: {sizes[CORE]['gzip']:,} gzip bytes, over {core_gzip_max:,}")

    ids = {name: obj.get("build_id") for name, (obj, _) in files.items()}
    if len(set(ids.values())) != 1 or not _HEX64.fullmatch(str(ids[CORE])):
        violations.append(f"build_id differs or is not 64 hex: {ids}")
    for shard in core.get("shards") or []:
        path = b_json / shard["path"] if (b_json / shard["path"]).is_file() else Path(b_site) / shard["path"]
        data = path.read_bytes() if path.is_file() else None
        if data is None or len(data) != shard.get("bytes") or hashlib.sha256(data).hexdigest() != shard.get("sha256"):
            violations.append(f"shard manifest entry {shard.get('path')} does not match the file")

    merged = merge(core, decade, detail)
    for key in sorted(set(a_payload) - {"schema_version", "orgs"}):
        if merged.get(key) != a_payload[key]:
            violations.append(f"header {key} differs")
    rows_a, rows_b = _rows(a_payload), _rows(merged)
    if set(rows_a) != set(rows_b):
        violations.append(f"row sets differ: {len(set(rows_a) - set(rows_b))} only in A, "
                          f"{len(set(rows_b) - set(rows_a))} only in B")
    decade_cols = merged["decade_columns"]
    decade_keys = {c["key"] for c in decade_cols}
    defaults = set(merged["decade_default_columns"])
    extra_ok = set(merged["amount_types"]) | set(merged["delta_columns"])

    added = Counter()
    org_split_added: dict[str, list[str]] = {}
    mismatches = 0
    for key in sorted(set(rows_a) & set(rows_b)):
        ra, rb = rows_a[key], rows_b[key]
        slug = key[1]
        for field in sorted((set(ra) | set(rb)) - ROW_META):
            if ra.get(field) != rb.get(field):
                violations.append(f"{slug}: {field} differs")
        for col, cell in ra["cells"].items():
            if rb["cells"].get(col) != cell:
                violations.append(f"{slug}: A cell {col} changed or missing in B")
        b_only = sorted(set(rb["cells"]) - set(ra["cells"]))
        nondecade = [c for c in b_only if c not in decade_keys]
        if nondecade:
            if slug in ORG_SPLIT_ROWS and set(nondecade) <= extra_ok:
                org_split_added[slug] = nondecade
            else:
                violations.append(f"{slug}: B adds non-decade cells {nondecade}")
        sidecar_path = Path(b_site) / "json" / "program_details" / f"{slug}.json"
        series = (json.loads(sidecar_path.read_text()).get("decade_series") or {}) if sidecar_path.is_file() else {}
        points = {(kind, p["edition"], p["fy"]): p for kind, pts in series.items() for p in pts}
        for col in decade_cols:
            cell, point = rb["cells"].get(col["key"]), points.get((col["kind"], col["edition"], col["fy"]))
            if (cell is None) != (point is None) or (cell and (cell["fid"], cell["v"]) != (point["fid"], point["v"])):
                mismatches += 1
                if mismatches <= SHOW:
                    violations.append(f"{slug}: leg j {col['key']} cell {cell} vs sidecar point "
                                      f"{None if point is None else {'fid': point['fid'], 'v': point['v']}}")
                continue
            if cell is not None and col["key"] not in ra["cells"]:
                era = "era" if col["edition"] <= ERA_LAST_EDITION else "modern"
                added[era] += 1
                if col["key"] in defaults:
                    added[f"{era}_default"] += 1
                if slug in ORG_SPLIT_ROWS:
                    added[f"{era}_org_split"] += 1
    if mismatches > SHOW:
        violations.append(f"... leg j: {mismatches} mismatches in all")
    return {"ok": not violations, "sizes": sizes, "build_id": ids[CORE],
            "rows": {"a": len(rows_a), "b": len(rows_b)},
            "decade_cells_added": {k: added.get(k, 0) for k in (
                "era", "modern", "era_default", "modern_default", "era_org_split", "modern_org_split")},
            "org_split_nondecade_added": org_split_added, "leg_j_mismatches": mismatches,
            "panel": {"a": _panel(a_payload, rows_a), "b": _panel(merged, rows_b)},
            "violations": violations}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="P2b: /years/ shards against the v1 matrix and the program sidecars")
    p.add_argument("--a", type=Path, required=True, help="data/site exported by the deployed code")
    p.add_argument("--b", type=Path, required=True, help="data/site exported by the follow-ups code, same snapshot")
    p.add_argument("--expect-era-added", type=int, default=None)
    p.add_argument("--expect-modern-added", type=int, default=None)
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        report = run(args.a, args.b)
    except Exception as e:  # noqa: BLE001 — a tool error is exit 2, never a verdict
        print(f"years-shard-proof: ERROR — {e}", file=sys.stderr)
        return 2
    got = report["decade_cells_added"]
    for flag, key in ((args.expect_era_added, "era"), (args.expect_modern_added, "modern")):
        if flag is not None and got[key] != flag:
            report["violations"].append(f"{key} decade cells added {got[key]:,}, expected {flag:,}")
    report["ok"] = not report["violations"]
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for name, s in report["sizes"].items():
        print(f"{name}: {s['bytes']:,} bytes, {s['gzip']:,} gzip")
    print(f"build_id {report['build_id']}; rows A {report['rows']['a']:,}, B {report['rows']['b']:,}; "
          f"leg j mismatches {report['leg_j_mismatches']:,}")
    print("decade cells added: " + ", ".join(f"{k} {v:,}" for k, v in got.items()))
    print(f"org-split rows' non-decade cells added: {json.dumps(report['org_split_nondecade_added'], sort_keys=True)}")
    for side in ("a", "b"):
        pn = report["panel"][side]
        print(f"totals-chart panel {side.upper()}: {pn['programs']:,} of {pn['of']:,} programs; "
              f"FY2024A->FY2026R {pn['fy2024a_to_fy2026r_pct']}%; first->last {pn['first_to_last_pct']}%")
    for v in report["violations"][:SHOW]:
        print(f"  violation: {v}")
    print(f"years-shard-proof: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_fu_fact_delta.py tests/test_fu_years_shard_proof.py -q && uvx --offline ruff check --isolated --select F,E9 scripts/fu/fact_delta.py scripts/fu/years_shard_proof.py tests/test_fu_fact_delta.py tests/test_fu_years_shard_proof.py`
Expected: `13 passed`, then `All checks passed!`. `test_the_real_split_round_trips_through_the_proof` exercises Task 13's `split_years_matrix`/`merge_years_matrix` and its two constants end to end; if it fails on an import or attribute error, Task 13's interface differs from the one this task consumes: stop and reconcile the names with Task 13's file, never stub them here.

- [ ] **Step 7: Smoke-test fact_delta on the live export against itself**

It reads only `data/site`, so it needs no SAM guard:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python scripts/fu/fact_delta.py --a "$GOVBUDGET_DATA/site" --b "$GOVBUDGET_DATA/site"
```
Expected (the live export, unless it was re-exported since 2026-10-04): `citations: A 143,841, B 143,841, new in B 0 {}, moved 0, noise-equivalent fields 0`, the three dataset lines (8,549 / 56,264 / 1,988 rows, `A rows not in B 0`, `{}`), `fact-delta: PASS`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/scripts/fu/fact_delta.py GovBudget/scripts/fu/years_shard_proof.py GovBudget/tests/test_fu_fact_delta.py GovBudget/tests/test_fu_years_shard_proof.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(fu): release-1 proof tools — fact delta (P1/P2) and the /years/ shard proof (P2b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `4 files changed`.
