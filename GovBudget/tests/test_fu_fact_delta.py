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
