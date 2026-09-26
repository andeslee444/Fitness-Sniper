"""ROADMAP #139 (code half): an eval run the PROVIDER blocked is BLOCKED, not
an accuracy failure.

From 2026-09-18 to the owner's top-up on 2026-09-25 the Anthropic key answered
HTTP 400 "credit balance is too low", every question came back ERROR at
$0.00, and `verify-phase5` reported "accuracy 0/48 < 44 threshold" with
`blocked: false` in the run record — a model failure the model never had the
chance to commit. `provider_block_reason` reads the run record and says
BLOCKED (with the cause) when, and only when, the questions the provider
refused could have changed the verdict. A run that fails on the questions it
DID answer still FAILs.

Fixture records under tests/fixtures/eval_runs/ are real run records copied
from the roadmap-completion worktree's data/research/eval-runs/ (untracked
there): 2026-09-25T06:29:47Z (all 48 ERROR, $0 — chain C run 4),
2026-09-18T21:09:26Z (27 correct, 20 ERROR at $0, 1 wrong — the day the
credit ran out; no error text recorded then) and 2026-09-25T16:09:43Z (46/48,
43/43, after the top-up).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from govbudget.verify_phase5 import (
    ACCURACY_THRESHOLD,
    _compute_exit_code,
    non_provider_error_clause,
    provider_block_reason,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "eval_runs"
CREDIT_TEXT = (
    "Error code: 400 - {'type': 'error', 'error': {'type': "
    "'invalid_request_error', 'message': 'Your credit balance is too low to "
    "access the Anthropic API. Please go to Plans & Billing to upgrade or "
    "purchase credits.'}}"
)
AUTH_TEXT = (
    "Error code: 401 - {'type': 'error', 'error': {'type': "
    "'authentication_error', 'message': 'invalid x-api-key'}}"
)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _score(i: int, *, correct=False, error=False, cost=0.05, text=None,
           cite=None) -> dict:
    s = {
        "id": f"q{i:03d}", "question": "q", "expected": "x",
        "agent_answer": "ERROR" if error else "x",
        "agent_error": error, "agent_refuse": error,
        "agent_refuse_class": None, "correct": correct,
        "citation_kind": "none" if error else "warehouse",
        "citation_resolved": None if error else (True if cite is None else cite),
        "citation_reason": None, "citation_retried": False,
        "citation_retry_attempts": None, "citation_retry_cost_usd": 0.0,
        "turns": 0 if error else 4, "cost_usd": 0.0 if error else cost,
    }
    if text is not None:
        s["agent_error_text"] = text
    return s


def _run(scores: list[dict]) -> dict:
    return {"scores": scores, "blocked": False, "ok": False}


# ---------------------------------------------------------------------------
# The real records
# ---------------------------------------------------------------------------


def test_the_real_all_error_zero_cost_run_is_blocked_not_an_accuracy_failure():
    run = _load("eval-20260925T062947Z.json")
    assert run["blocked"] is False and run["accuracy"] == 0, "fixture is the defect"
    reason = provider_block_reason(run)
    assert reason is not None, "48 ERROR at $0.00 measured nothing about the model"
    assert "48 of 48" in reason
    assert "$0.00" in reason
    assert "accuracy" not in reason.split("—")[0].lower(), (
        "the headline must name the block, not an accuracy score")


def test_a_real_passing_run_is_not_blocked():
    run = _load("eval-20260925T160943Z.json")
    assert provider_block_reason(run) is None


def test_a_real_partial_run_without_error_text_still_fails():
    """27 correct, 20 ERROR at $0 and 1 wrong, recorded before the error text
    was kept. Not every question errored, and nothing in the record says the
    20 were the provider's refusal — so this stays a FAIL: BLOCKED needs
    evidence, and a code crash on 20 questions reads exactly the same."""
    run = _load("eval-20260918T210926Z.json")
    assert provider_block_reason(run) is None


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


def test_a_real_accuracy_failure_still_fails():
    """40/48 answered and scored, no errors, money spent: a model failure."""
    scores = [_score(i, correct=i < 40) for i in range(48)]
    assert provider_block_reason(_run(scores)) is None


def test_provider_credit_text_blocks_a_partial_run_that_could_still_pass():
    """Credit ran out after 28 answers, every one correct: 28 correct + 20
    refused by the provider could still reach 44, and every question that is
    not correct is a refusal, so the verdict is undetermined."""
    scores = ([_score(i, correct=True) for i in range(28)]
              + [_score(28 + i, error=True, text=CREDIT_TEXT) for i in range(20)])
    reason = provider_block_reason(_run(scores))
    assert reason is not None
    assert "20 of 48" in reason
    assert "credit balance is too low" in reason


def test_a_wrong_answer_beside_the_refusals_is_a_fail():
    """R-DEC-139b: BLOCKED only when EVERY question that is not correct is a
    provider refusal. 27 correct + 20 refused + 1 answered WRONG: the wrong
    answer is the model's, not the provider's, so this is a FAIL (the stage-1
    rule called it BLOCKED because 27 + 20 >= 44)."""
    scores = ([_score(i, correct=True) for i in range(27)]
              + [_score(27 + i, error=True, text=CREDIT_TEXT) for i in range(20)]
              + [_score(47)])
    assert 27 + 20 >= ACCURACY_THRESHOLD
    assert provider_block_reason(_run(scores)) is None


def test_checker_case_1_credit_ran_out_mid_run_is_blocked_under_the_rule():
    """The stage-1 checker's case (1): 40 answered, all correct ($0.60 spent),
    then 8 credit refusals. Every question that is not correct is a provider
    refusal and 40 + 8 >= 44, so under R-DEC-139b's rule as written the
    refusals alone decide the verdict: BLOCKED (exit 2, still non-zero).
    Spend is not part of the rule: a credit balance runs out MID-run, after
    money was spent, exactly as it did on 2026-09-18."""
    scores = ([_score(i, correct=True, cost=0.015) for i in range(40)]
              + [_score(40 + i, error=True, text=CREDIT_TEXT) for i in range(8)])
    reason = provider_block_reason(_run(scores))
    assert reason is not None
    assert "8 of 48" in reason and "$0.60" in reason
    assert non_provider_error_clause(_run(scores)) is None


def test_checker_case_2_refusals_mixed_with_code_crashes_is_a_fail():
    """The stage-1 checker's case (2): 42 correct, 2 credit refusals and 4
    TypeErrors at $0.63. 42 + 2 >= 44, but the 4 crashes are not the
    provider's: FAIL, and the message names them (the stage-1 rule said
    BLOCKED and left the crashes out)."""
    scores = ([_score(i, correct=True, cost=0.015) for i in range(42)]
              + [_score(42 + i, error=True, text=CREDIT_TEXT) for i in range(2)]
              + [_score(44 + i, error=True, text="TypeError: bad operand type")
                 for i in range(4)])
    run = _run(scores)
    assert provider_block_reason(run) is None
    clause = non_provider_error_clause(run)
    assert clause is not None
    assert clause.startswith("4 of 48 questions errored with no provider refusal")
    for qid in ("q044", "q045", "q046", "q047"):
        assert qid in clause
    assert "TypeError: bad operand type" in clause
    assert "2 other(s) were refused by the provider" in clause


def test_provider_block_that_cannot_rescue_the_verdict_is_a_fail():
    """30 correct + 5 refused < 44: the run already proved the failure, so
    calling it BLOCKED would hide a real accuracy failure behind a top-up."""
    scores = ([_score(i, correct=True) for i in range(30)]
              + [_score(30 + i, error=True, text=CREDIT_TEXT) for i in range(5)]
              + [_score(35 + i) for i in range(13)])
    assert 30 + 5 < ACCURACY_THRESHOLD
    assert provider_block_reason(_run(scores)) is None


def test_a_citation_failure_among_answered_questions_is_a_fail():
    """Citation resolution must be 100%; one proven miss decides the gate."""
    scores = ([_score(i, correct=True) for i in range(40)]
              + [_score(40, correct=True, cite=False)]
              + [_score(41 + i, error=True, text=CREDIT_TEXT) for i in range(7)])
    assert provider_block_reason(_run(scores)) is None


def test_an_auth_refusal_blocks_too():
    scores = [_score(i, error=True, text=AUTH_TEXT) for i in range(48)]
    reason = provider_block_reason(_run(scores))
    assert reason is not None and "invalid x-api-key" in reason


def test_errors_with_non_provider_text_and_spend_are_not_blocked():
    """A crash that is not the provider's refusal (a TypeError in the agent)
    on part of the run is the code's failure, not a block."""
    scores = ([_score(i, correct=True) for i in range(40)]
              + [_score(40 + i, error=True, text="TypeError: bad operand")
                 for i in range(8)])
    assert provider_block_reason(_run(scores)) is None


def test_an_all_error_zero_cost_run_whose_text_is_a_code_crash_fails():
    """The $0 shape stands in for evidence only where no text was recorded.
    A TypeError on every question before any API call is the code's failure,
    and the record now says so."""
    scores = [_score(i, error=True, text="TypeError: bad operand") for i in range(48)]
    assert provider_block_reason(_run(scores)) is None


def test_the_crash_clause_names_errors_that_carry_no_text():
    """A record kept no text before 2026-09-25: its errors are named as
    errors with no provider refusal on record — never called crashes or
    refusals the record does not show."""
    run = _load("eval-20260918T210926Z.json")
    clause = non_provider_error_clause(run)
    assert clause is not None
    assert clause.startswith("20 of 48 questions errored with no provider refusal")
    assert "no error text recorded" in clause
    assert "refused by the provider" not in clause


def test_the_crash_clause_is_none_on_a_block_and_on_a_clean_run():
    assert non_provider_error_clause(_load("eval-20260925T062947Z.json")) is None
    scores = [_score(i, correct=i < 40) for i in range(48)]
    assert non_provider_error_clause(_run(scores)) is None


def test_the_crash_clause_lists_at_most_five_and_counts_the_rest():
    scores = ([_score(i, correct=True) for i in range(40)]
              + [_score(40 + i, error=True, text=f"TypeError: t{i}")
                 for i in range(8)])
    clause = non_provider_error_clause(_run(scores))
    assert "q040" in clause and "q044" in clause
    assert "q045" not in clause
    assert "and 3 more" in clause


def test_an_empty_record_is_not_blocked_by_this_rule():
    assert provider_block_reason({"scores": []}) is None
    assert provider_block_reason({}) is None


# ---------------------------------------------------------------------------
# eval_gate applies it, keeps the cause, and the exit code stays non-zero
# ---------------------------------------------------------------------------


def _agent_raising(text: str):
    """agent.run as it behaves when messages.create raises: the SDK's error
    propagates out of the retry loop (a 400/401 is not retried)."""
    def _run(question, **_kw):
        raise RuntimeError(text)
    return _run


def _one_question_yaml(tmp_path: Path, n: int) -> Path:
    entries = [{
        "id": f"q{i:03d}", "question": "Which company?",
        "answer_sql": "select 1", "expected_answer": "X",
        "expected_citation_kind": "warehouse", "notes": "t",
    } for i in range(n)]
    p = tmp_path / "evals" / "phase5_questions.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(entries))
    return p


def test_eval_gate_reports_a_credit_refused_run_as_blocked_with_the_cause(
    tmp_path, monkeypatch
):
    import govbudget.verify_phase5 as vp5

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setattr(vp5, "EVAL_PATH", _one_question_yaml(tmp_path, 48))
    monkeypatch.setattr("govbudget.analyst.agent.run", _agent_raising(CREDIT_TEXT))
    result = vp5.eval_gate(client=object(), duckdb_path=tmp_path / "none.duckdb")
    assert result["blocked"] is True
    assert result["ok"] is False
    assert result["block_cause"] == "provider"
    assert "credit balance is too low" in result["reason"]
    # The record keeps each question's cause, so a later reader of the JSON
    # (the thing #139 complained about) sees why without re-running.
    assert all("credit balance" in s["agent_error_text"] for s in result["scores"])
    # Never exit 0 on a blocked eval.
    ag = {"ok": True, "blocked": False, "all_blocked_phases": [], "results": []}
    assert _compute_exit_code(fg_ok=True, eg=result, ag=ag) == 2


def test_eval_gate_fails_a_run_mixing_refusals_and_crashes_and_names_them(
    tmp_path, monkeypatch
):
    """R-DEC-139b at the gate: refusals on some questions and a code crash
    on another is a FAIL (exit 1), and the reason names the crash."""
    import govbudget.verify_phase5 as vp5

    calls = {"n": 0}

    def _agent(question, **_kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TypeError("unsupported operand type(s) for +: 'int' and 'str'")
        raise RuntimeError(CREDIT_TEXT)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setattr(vp5, "EVAL_PATH", _one_question_yaml(tmp_path, 48))
    monkeypatch.setattr("govbudget.analyst.agent.run", _agent)
    result = vp5.eval_gate(client=object(), duckdb_path=tmp_path / "none.duckdb")
    assert result["blocked"] is False
    assert result["ok"] is False
    assert "q000" in result["reason"]
    assert "unsupported operand" in result["reason"]
    assert "47 other(s) were refused by the provider" in result["reason"]
    ag = {"ok": True, "blocked": False, "all_blocked_phases": [], "results": []}
    assert _compute_exit_code(fg_ok=True, eg=result, ag=ag) == 1


def test_cmd_prints_the_crash_clause_on_a_fail(tmp_path, monkeypatch, capsys):
    import govbudget.verify_phase5 as vp5

    scores = ([_score(i, correct=True) for i in range(42)]
              + [_score(42 + i, error=True, text=CREDIT_TEXT) for i in range(2)]
              + [_score(44 + i, error=True, text="TypeError: bad operand type")
                 for i in range(4)])
    failed = {"ok": False, "blocked": False, "scores": scores,
              "accuracy": 42, "total": 48, "citation_ok": 42,
              "citation_total": 42, "citation_retry_count": 0,
              "citation_retry_total_cost_usd": 0.0,
              "reason": "accuracy 42/48 < 44 threshold; "
                        + non_provider_error_clause(_run(scores))}
    monkeypatch.setattr(vp5, "freshness_gate",
                        lambda **_: {"ok": True, "ok_ids": [], "stale": [], "errors": []})
    monkeypatch.setattr(vp5, "eval_gate", lambda **_: copy.deepcopy(failed))
    monkeypatch.setattr(vp5, "assembly_gate", lambda **_: {
        "ok": True, "blocked": False, "all_blocked_phases": [], "results": []})
    monkeypatch.setattr(vp5.config, "RESEARCH_DIR", tmp_path)
    with pytest.raises(SystemExit) as exc:
        vp5.cmd_verify_phase5(SimpleNamespace())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "gate eval: 4 of 48 questions errored with no provider refusal" in out
    assert "error='TypeError: bad operand type'" in out


def test_the_error_text_never_carries_an_api_key(tmp_path, monkeypatch):
    import govbudget.verify_phase5 as vp5

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setattr(vp5, "EVAL_PATH", _one_question_yaml(tmp_path, 1))
    monkeypatch.setattr("govbudget.analyst.agent.run", _agent_raising(
        "bad key sk-ant-api03-ABCdef_123-xyz rejected"))
    result = vp5.eval_gate(client=object(), duckdb_path=tmp_path / "none.duckdb")
    text = result["scores"][0]["agent_error_text"]
    assert "sk-ant-api03-ABCdef_123-xyz" not in text
    assert "sk-ant-…" in text


def test_cmd_persists_a_blocked_run_that_actually_ran(tmp_path, monkeypatch, capsys):
    """A provider-blocked run spent (or tried to spend) money and is evidence;
    only the no-key BLOCKED (nothing ran) goes unrecorded."""
    import govbudget.verify_phase5 as vp5

    blocked = {"ok": False, "blocked": True, "block_cause": "provider",
               "scores": [_score(0, error=True, text=CREDIT_TEXT)],
               "accuracy": 0, "total": 1, "citation_ok": 0, "citation_total": 0,
               "citation_retry_count": 0, "citation_retry_total_cost_usd": 0.0,
               "reason": "eval run BLOCKED by the provider — 1 of 1 …"}
    monkeypatch.setattr(vp5, "freshness_gate",
                        lambda **_: {"ok": True, "ok_ids": [], "stale": [], "errors": []})
    monkeypatch.setattr(vp5, "eval_gate", lambda **_: copy.deepcopy(blocked))
    monkeypatch.setattr(vp5, "assembly_gate", lambda **_: {
        "ok": True, "blocked": False, "all_blocked_phases": [], "results": []})
    monkeypatch.setattr(vp5.config, "RESEARCH_DIR", tmp_path)
    with pytest.raises(SystemExit) as exc:
        vp5.cmd_verify_phase5(SimpleNamespace())
    assert exc.value.code == 2
    written = list((tmp_path / "eval-runs").glob("eval-*.json"))
    assert len(written) == 1
    rec = json.loads(written[0].read_text())
    assert rec["blocked"] is True and rec["block_cause"] == "provider"
    out = capsys.readouterr().out
    assert "gate eval: BLOCKED — eval run BLOCKED by the provider" in out
    assert "ANTHROPIC_API_KEY" not in out.split("verify-phase5: BLOCKED")[1], (
        "the unblock step must name the provider's refusal, not a missing key")
