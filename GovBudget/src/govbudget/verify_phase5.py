"""Phase 5B-4 acceptance gates: NL eval + cross-phase assembly.

Gates (CLI: verify-phase5):

  1. freshness_gate  — re-runs every non-REFUSE answer_sql against the live
     DuckDB and fails loud if any expected_answer is stale. Runs FIRST so the
     eval_gate operates on a correct expected set.

  2. eval_gate  — runs the analyst agent over all 48 questions (BLOCKED when
     ANTHROPIC_API_KEY is absent). Scores accuracy (≥44/48 = 91.7%, tolerance-
     aware, canonical string compare). REFUSE questions: agent.refuse AND exact
     expected_refuse_class match. Citation resolution: for every non-REFUSE
     answered question, re-executes agent.sql through a fresh SqlTool instance
     (sandboxed, cwd-correct), validates non-empty touched_tables, touched ∩
     tables(answer_sql) non-empty, recomputed answer matches agent.answer AND
     (when the answer scored correct) the EXPECTED answer within tolerance.
     pdf_page citation: citations.parquet lookup on (pe_bli, canonical
     amount_text) with page_number non-null. source_url citation: per-table
     URL-column map. 100% resolution required — never lowered. A question
     that scored correct but failed resolution ONLY because the agent's
     final SQL was a literal echo (empty touched_tables — backlog #36, a
     twice-observed agent-sampling flake, not a build defect) gets ONE
     bounded, recorded retry that genuinely re-samples the agent for that
     question (resolve_citation_with_retry / _citation_retry_recompute) —
     this is real, disclosed, narrowly-scoped API spend, never a re-run of
     the same frozen SQL (which is a mathematical no-op, see the retry's own
     docstring). A wrong answer, a REFUSE, or an `error: True` crash never
     triggers it. `retried`/`attempts` are persisted per question so a
     retried pass is never invisible in the eval-run artifact.

  3. assembly_gate — subprocess-invokes verify-phase{1,2,3,4,5a,5b1,5b3} (NOT
     5b2 — 5b3 runs the same npm suite) PLUS verify-lineage (the program-
     lineage honesty legs a–e; its leg d audits the built export, so a
     missing built artifact FAILs the leg — same treatment as the other
     build-dependent phase gates) PLUS verify-era-map (families piece 1,
     legs a–f: the era P-1 workbooks re-read against the map, no undecided
     or stale decision, F-15's era rows, every budget_lines_decade fact ID
     recomputed from its own row, the published map equal to the
     warehouse's, the F-15 history sha pinned; legs d–f audit the export,
     so a missing artifact FAILs). Parses each full output with the verdict
     regex; BLOCKED propagates. Prints a result table.

Exit codes:
  0  — all gates PASS
  2  — all gates either PASS or BLOCKED (nothing FAILED), printing the single
       unblock step
  1  — any gate FAILs

BLOCKED behavior: eval_gate → BLOCKED without key, and BLOCKED (with the
provider's own error text) when the provider refused enough of the run that its
verdict was never measured — e.g. every question ERROR at $0.00 on an empty
credit balance (ROADMAP #139, provider_block_reason); assembly propagates
BLOCKED from sub-phases. Nothing is a hard FAIL if the only issue is a missing
API key or a refused one; a run that already failed on the questions it did
answer is still a FAIL.

All gate functions take explicit paths — no config read at module level.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from govbudget import config
from govbudget.evals_refresh import _within_tolerance, _canonicalize, _run_sql
from govbudget.analyst.sql_tool import KNOWN_TABLES, SqlError, SqlTool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_PATH = Path(__file__).resolve().parents[2] / "evals" / "phase5_questions.yaml"

# Accuracy threshold: 44/48 ≈ 91.7% (raised from 41/45 when the 5E Task 9
# decade questions were added — the relative bar must never loosen as the
# question set grows)
ACCURACY_THRESHOLD = 44

REFUSE_CLASSES = frozenset({"data_not_ingested", "structurally_absent", "classified"})

# Marts that own the SAME jbook budget quantities at different grains. The 5E
# decade backfill made fct_decade_series a second canonical surface for
# per-PE fiscal-year amounts (fct_budget_trajectory a third for the FY25→26
# deltas); an agent citing any surface in a group is citing the same fact
# family, so the table-overlap precheck expands both sides through the group
# before intersecting. This is a scope extension, NOT a weakening: the
# value-recompute check below is untouched — the agent's fresh SQL must still
# reproduce its exact answer, and unrelated tables still fail the overlap.
TABLE_EQUIVALENCE_GROUPS: list[frozenset[str]] = [
    frozenset({"fct_budget_lines", "fct_decade_series", "fct_budget_trajectory"}),
]


def _expand_equivalence(tables: set[str]) -> set[str]:
    out = set(tables)
    for group in TABLE_EQUIVALENCE_GROUPS:
        if out & group:
            out |= group
    return out

# Canonical amount_text formatter for citations.parquet lookup
# f"{millions:,.3f}" e.g. "293.145" or "1,234.567"
def _canonical_amount_text(millions: float) -> str:
    return f"{millions:,.3f}"

# Exact reason string _resolve_citation returns when the recompute step's
# touched_tables comes back empty (literal/echo agent SQL). Shared with the
# citation-retry wiring below so the two can never drift apart.
_EMPTY_TOUCHED_REASON = "recompute: empty touched_tables (literal/echo SQL)"

# Per-table URL-column map (binding from plan rev-2 recon facts)
# key = table name in KNOWN_TABLES, value = column name with URL
_URL_COLUMN_MAP: dict[str, str] = {
    "improper_payments": "source_url",
    "fct_state_per_capita": "spend_source_url",   # state spend questions
    "high_risk": "source_url",                    # GAO high-risk
}
# Population-related questions: use url_column='pop_source_url' in the eval entry
# (q037 sets url_column: pop_source_url; state spend questions use map default)

# Sub-phases to check in assembly gate (NOT 5b2 — 5b3 runs same npm suite).
# verify-lineage (the 24th gate — program-lineage honesty legs a–e) is part of
# the automated assembly, not a manual-only CLI a release could skip. Its leg
# (d) audits the BUILT export artifact, so a missing/stale build FAILs the
# leg (and thus this assembly) — consistent with how the other build-dependent
# phase gates already behave (they FAIL on missing artifacts, never skip).
# verify-era-map (families piece 1, spec 2026-10-02 V4/V10) joins on the same
# terms: invoked with no arguments (its CLI defaults to config.SITE_DIR, the
# warehouse and the repo seed), one final "verify-era-map: PASS|FAIL" line.
_ASSEMBLY_PHASES = [
    "verify-phase1",
    "verify-phase2",
    "verify-phase3",
    "verify-phase4",
    "verify-phase5a",
    "verify-phase5b1",
    "verify-phase5b3",
    "verify-lineage",
    "verify-era-map",
]

# Verdict token regex: parse full output for verdict line. Matches the
# verify-phaseN family, verify-lineage and verify-era-map (whose CLIs print
# "verify-lineage: PASS|FAIL" / "verify-era-map: PASS|FAIL" in the same
# verdict-line format).
_VERDICT_RE = re.compile(
    r"verify-(?:phase\w+|lineage|era-map):\s*(PASS|FAIL|BLOCKED)", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Gate 1: Freshness gate
# ---------------------------------------------------------------------------


def freshness_gate(*, duckdb_path: Path | None = None) -> dict:
    """Re-run every non-REFUSE answer_sql; fail if any expected_answer is stale.

    Returns:
        ok (bool), stale (list of (id, expected, live)), errors (list of (id, err))
    """
    import duckdb as _duckdb

    db_path = duckdb_path or config.DUCKDB_PATH
    entries = _load_yaml()
    con = _duckdb.connect(str(db_path), read_only=True)

    stale: list[tuple[str, str, str]] = []
    errors: list[tuple[str, str]] = []
    ok_ids: list[str] = []
    skipped: list[str] = []

    for entry in entries:
        eid = entry["id"]
        if entry.get("expected_answer") == "REFUSE":
            skipped.append(eid)
            continue
        sql = entry.get("answer_sql", "").strip()
        if not sql:
            skipped.append(eid)
            continue
        try:
            rows = _run_sql(con, sql)
            live = _canonicalize(rows)
        except Exception as exc:
            errors.append((eid, str(exc)))
            continue

        expected = str(entry.get("expected_answer", ""))
        tolerance = entry.get("tolerance")
        if _within_tolerance(live, expected, tolerance):
            ok_ids.append(eid)
        else:
            stale.append((eid, expected, live))

    con.close()
    return {
        "ok": not stale and not errors,
        "stale": stale,
        "errors": errors,
        "ok_ids": ok_ids,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Gate 2: Eval gate (scoring + citation resolution)
# ---------------------------------------------------------------------------


def _load_yaml() -> list[dict]:
    with open(EVAL_PATH) as fh:
        return yaml.safe_load(fh)


def _score_answer(agent_result: dict, entry: dict) -> bool:
    """Return True if the agent's answer is correct for this entry.

    For REFUSE entries: agent.refuse must be True AND exact enum match on
    expected_refuse_class.
    For answered entries: canonical string compare within tolerance.
    """
    # An agent CRASH is not a judgment (2026-08-13). The except-handler below
    # used to synthesise {"refuse": True, "refuse_reason_class":
    # "structurally_absent"} from any exception, so a question the agent never
    # ran — turns=0, cost=$0.00 — scored CORRECT against every REFUSE entry.
    # Measured on eval-20260813T012743Z: q042 (THAAD bid prices) errored with
    # zero turns and was counted as a correct refusal, silently inflating
    # refusal coverage. An error can never be right about anything.
    if agent_result.get("error", False):
        return False

    expected = str(entry.get("expected_answer", ""))
    if expected == "REFUSE":
        if not agent_result.get("refuse", False):
            return False
        return agent_result.get("refuse_reason_class") == entry.get("expected_refuse_class")
    else:
        if agent_result.get("refuse", False):
            return False
        agent_answer = str(agent_result.get("answer", ""))
        tolerance = entry.get("tolerance")
        return _within_tolerance(agent_answer, expected, tolerance)


def _resolve_citation(
    agent_result: dict,
    entry: dict,
    *,
    duckdb_path: Path | None = None,
    citations_parquet: Path | None = None,
    is_correct: bool,
) -> dict:
    """Resolve the citation for an answered (non-REFUSE) question.

    Returns:
        ok (bool), reason (str)

    Resolution rules:
    - Re-execute agent.sql through a FRESH SqlTool instance (sandboxed).
    - touched_tables must be non-empty.
    - touched ∩ tables(answer_sql) must be non-empty.
    - Recomputed answer must match agent.answer.
    - When the answer scored correct: recomputed must also match EXPECTED within
      tolerance.
    - pdf_page: citations.parquet lookup on (pe_bli, canonical amount_text)
      with page_number non-null. Requires pe_bli + amount_text columns in
      citations.parquet (Task 4 adds them).
    - source_url: per-table URL-column map via fresh SqlTool.
    """
    if agent_result.get("refuse", False):
        # REFUSE questions — citation resolution is not evaluated
        return {"ok": True, "reason": "skipped (REFUSE)"}

    agent_sql = agent_result.get("sql")
    citation_kind = agent_result.get("citation_kind", "none")
    citation = agent_result.get("citation")

    if not agent_sql:
        if citation_kind in ("none", "warehouse") and not agent_result.get("answer"):
            return {"ok": False, "reason": "agent provided no SQL and no answer"}
        # No SQL and citation_kind == 'none' — treat as unresolvable
        return {"ok": False, "reason": "agent provided no SQL for answered question"}

    # --- Re-execute through fresh SqlTool ---
    db_path = duckdb_path or config.DUCKDB_PATH
    try:
        with SqlTool(db_path) as fresh_tool:
            result = fresh_tool.run(agent_sql)
    except SqlError as exc:
        return {"ok": False, "reason": f"recompute SQL rejected by gate: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"recompute SQL failed: {exc}"}

    touched = result.get("touched_tables", set())
    recomputed_rows = result.get("rows", [])
    recomputed = _canonicalize([tuple(r) for r in recomputed_rows]) if recomputed_rows else ""

    # touched_tables must be non-empty
    if not touched:
        return {"ok": False, "reason": _EMPTY_TOUCHED_REASON}

    # touched ∩ tables(answer_sql) must be non-empty
    # Extract tables from the ENTRY's answer_sql (the correct SQL)
    entry_sql = entry.get("answer_sql", "")
    entry_tokens = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", entry_sql)) & KNOWN_TABLES
    if not (_expand_equivalence(touched) & _expand_equivalence(entry_tokens)):
        return {
            "ok": False,
            "reason": (
                f"recompute: touched_tables {touched} does not overlap "
                f"tables in answer_sql {entry_tokens}"
            ),
        }

    # Recomputed must match agent.answer
    agent_answer = str(agent_result.get("answer", ""))
    tolerance = entry.get("tolerance")
    if not _within_tolerance(recomputed, agent_answer, tolerance):
        return {
            "ok": False,
            "reason": (
                f"recompute mismatch: fresh SQL returned {recomputed!r} "
                f"but agent claimed {agent_answer!r}"
            ),
        }

    # When scored correct: recomputed must also match EXPECTED
    if is_correct:
        expected = str(entry.get("expected_answer", ""))
        if not _within_tolerance(recomputed, expected, tolerance):
            return {
                "ok": False,
                "reason": (
                    f"recompute-vs-expected mismatch: fresh SQL returned {recomputed!r} "
                    f"but expected {expected!r}"
                ),
            }

    # --- Citation-kind specific resolution ---
    if citation_kind == "pdf_page":
        return _resolve_pdf_page(agent_result, entry, citations_parquet=citations_parquet)
    elif citation_kind == "source_url":
        # Pass per-question url_column override when present (e.g. pop_source_url for q037)
        return _resolve_source_url(
            agent_result, touched, db_path=db_path,
            url_column=entry.get("url_column"),
        )
    elif citation_kind in ("warehouse", "none"):
        # Warehouse / none: SQL re-execution is sufficient
        return {"ok": True, "reason": f"recomputed ok via {citation_kind}"}
    elif citation_kind == "filing_uuid":
        # LDA filing UUID — verify citation is non-empty
        if not citation:
            return {"ok": False, "reason": "filing_uuid citation is empty"}
        return {"ok": True, "reason": "filing_uuid citation present"}
    else:
        return {"ok": False, "reason": f"unknown citation_kind: {citation_kind!r}"}


def _resolve_pdf_page(
    agent_result: dict,
    entry: dict,
    *,
    citations_parquet: Path | None = None,
) -> dict:
    """Resolve a pdf_page citation against citations.parquet.

    Redesigned to resolve against the AGENT's answer rather than the entry's
    expected_answer, which prevents crashes on compound answers ("Iron Dome, 3080")
    and unit mismatches (billions vs millions).

    Resolution: match citations.parquet on pe_bli alone (extracted from the
    agent's citation string or SQL), requiring page_number non-null. The pe_bli
    is the authoritative key — wrong pe_bli still fails even if amounts match.

    Schema requirement: citations.parquet must have a pe_bli column (added by
    export-site pipeline). If absent, fails with an actionable message.
    """
    import duckdb as _duckdb

    cit_path = citations_parquet or (
        config.ROOT / "data" / "site" / "citations" / "citations.parquet"
    )
    if not Path(cit_path).exists():
        return {"ok": False, "reason": f"citations.parquet not found: {cit_path}"}

    # Extract pe_bli from agent's citation string or SQL.
    # Intentionally does NOT use entry.expected_answer to avoid:
    #   (a) float() crash on compound answers like "Iron Dome, 3080"
    #   (b) unit mismatch when expected is in billions but citations in millions
    citation = agent_result.get("citation", "") or ""
    agent_sql = agent_result.get("sql", "") or ""
    pe_bli = _extract_pe_bli(citation, agent_sql)

    if not pe_bli:
        return {"ok": False, "reason": "pdf_page: could not extract pe_bli from agent citation/SQL"}

    try:
        con = _duckdb.connect()
        # Check for pe_bli column — graceful fail if absent
        cols = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{cit_path}')"
        ).fetchall()]

        if "pe_bli" not in cols:
            con.close()
            return {
                "ok": False,
                "reason": (
                    "pdf_page: citations.parquet has no pe_bli column — "
                    "re-run `govbudget export-site` after Task 4 is applied"
                ),
            }

        # Match on pe_bli alone — the authoritative key for J-book page lookup.
        # wrong pe_bli → no row → fails (even if the amount would match).
        rows = con.execute(
            f"""
            SELECT page_number FROM read_parquet('{cit_path}')
            WHERE kind = 'jbook_pdf'
              AND pe_bli = ?
              AND page_number IS NOT NULL
            LIMIT 1
            """,
            [pe_bli],
        ).fetchall()
        con.close()

        if not rows:
            return {
                "ok": False,
                "reason": (
                    f"pdf_page: no citation row for pe_bli={pe_bli!r} "
                    f"(or page_number is null)"
                ),
            }
        page = rows[0][0]
        return {"ok": True, "reason": f"pdf_page: page {page} found for pe_bli={pe_bli!r}"}

    except Exception as exc:
        return {"ok": False, "reason": f"pdf_page lookup error: {exc}"}


def _extract_pe_bli(citation: str, sql: str) -> str | None:
    """Extract pe_bli from agent's citation string or SQL.

    Looks for a PE number pattern like '0601101E' or '1160401BB'.
    """
    # Try citation text first
    m = re.search(r"\b([0-9]{6,7}[A-Z]{1,3})\b", citation or "")
    if m:
        return m.group(1)
    # Try SQL
    m = re.search(r"pe_bli\s*=\s*['\"]([^'\"]+)['\"]", sql or "", re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\b([0-9]{6,7}[A-Z]{1,3})\b", sql or "")
    if m:
        return m.group(1)
    return None


def _resolve_source_url(
    agent_result: dict,
    touched: set[str],
    *,
    db_path: Path | None = None,
    url_column: str | None = None,
) -> dict:
    """Resolve a source_url citation via the per-table URL-column map.

    When url_column is provided (from the eval entry's optional url_column field),
    it overrides the per-table map default. This is used for population questions
    (q037) where fct_state_per_capita has both spend_source_url (map default) and
    pop_source_url (the correct column for population-derived answers).

    Runs a fresh SqlTool query to fetch a non-empty URL from the touched table.
    """
    # Determine which table to look up the URL from
    url_table = None
    url_col = None

    # Find first touched table that has a URL column
    for tbl in touched:
        if tbl in _URL_COLUMN_MAP:
            url_table = tbl
            # Per-question url_column override takes precedence over map default
            url_col = url_column if url_column is not None else _URL_COLUMN_MAP[tbl]
            break

    if not url_table:
        return {
            "ok": False,
            "reason": (
                f"source_url: no URL-column mapping for touched tables {touched}; "
                f"known map: {list(_URL_COLUMN_MAP.keys())}"
            ),
        }

    # Verify the URL column exists and has a non-empty value
    real_db = db_path or config.DUCKDB_PATH
    try:
        with SqlTool(real_db) as t:
            result = t.run(
                f"SELECT {url_col} FROM {url_table} WHERE {url_col} IS NOT NULL LIMIT 1"
            )
        rows = result.get("rows", [])
        if not rows or not rows[0][0]:
            return {
                "ok": False,
                "reason": f"source_url: {url_table}.{url_col} has no non-empty URL",
            }
        return {"ok": True, "reason": f"source_url: found via {url_table}.{url_col}"}
    except SqlError as exc:
        return {"ok": False, "reason": f"source_url lookup SQL error: {exc}"}
    except Exception as exc:
        return {"ok": False, "reason": f"source_url lookup error: {exc}"}


# ---------------------------------------------------------------------------
# Bounded, recorded citation-resolution retry (backlog #36)
# ---------------------------------------------------------------------------
#
# verify-phase5's citation gate is a 100% bar sampled ONCE from a
# nondeterministic LLM agent. q011 has flaked twice: the agent's final
# submit_answer(sql=...) is occasionally a literal echo ("SELECT 293.145",
# no FROM/JOIN) even when the ANSWER is correct, which leaves touched_tables
# empty and the citation unresolvable. An immediate re-run of the same gate
# against the SAME build/data scored 43/43 — the build was never wrong.


def resolve_citation_with_retry(question_id, recompute, max_attempts=2):
    """Retry a citation-resolution attempt, bounded, and only when it came
    back empty.

    This is a GENERIC primitive: `recompute` is caller-defined — it is not
    prescribed to mean "re-execute the same frozen SQL string." That
    distinction matters. `_extract_touched_tables` (analyst/sql_tool.py) is a
    pure regex function of the SQL TEXT alone: re-running the exact same
    `agent.sql` through a fresh SqlTool reproduces byte-identical
    touched_tables on every call, forever — a literal-echo SQL string has no
    FROM/JOIN to extract, so a "retry" that only re-executes that string is a
    mathematical no-op for the flake this exists to fix. `_citation_retry_recompute`
    below is the actual `recompute` this project wires in: it re-samples the
    AGENT for the one flaky question (a genuine, and genuinely paid, retry),
    not the frozen SQL. See its docstring for the full argument and the cost
    disclosure.

    A citation that does not resolve is still a failure — this does not
    lower the bar. It distinguishes "the agent echoed a literal on this
    sample" from "the build has no citation," which a single sample cannot.
    Every retry is recorded (`retried`, `attempts`) so a retried pass is
    never mistaken for a clean one.
    """
    result = recompute(question_id)
    if result.get("touched_tables"):
        return {**result, "retried": False, "attempts": 1}
    for attempt in range(2, max_attempts + 1):
        result = recompute(question_id)
        if result.get("touched_tables"):
            return {**result, "retried": True, "attempts": attempt}
    return {**result, "retried": True, "attempts": max_attempts}


def _error_agent_result(reason: str) -> dict:
    """Same error shape eval_gate's own except-handler builds (commit
    e243f51) — `error: True` disqualifies unconditionally in `_score_answer`.
    """
    return {
        "answer": "ERROR",
        "error": True,
        "refuse": True,
        "refuse_reason_class": None,
        "sql": None,
        "citation_kind": "none",
        "citation": reason,
        "turns": 0,
        "cost_usd": 0.0,
        "touched_tables": set(),
    }


def _citation_retry_recompute(
    question: str,
    entry: dict,
    *,
    agent_run_fn,
    client,
    duckdb_path: Path | None,
    citations_parquet: Path | None,
    first_result: dict,
    first_is_correct: bool,
    first_citation: dict,
):
    """Build the `recompute` callable passed to resolve_citation_with_retry.

    COST DISCLOSURE: attempt 1 is FREE — it reuses the agent_run() the main
    eval_gate loop already paid for (the caller only invokes this factory
    once it already knows attempt 1 failed with the empty-touched-tables
    reason, so nothing is wasted re-deriving that). Attempt 2+ (bounded by
    max_attempts, so at most ONE extra call per question given this
    project's max_attempts=2) calls the REAL agent again — a genuine,
    non-zero API cost (~$0.01-0.02 for one question's turns, vs ~$0.55-0.85
    for a full 48-question eval run). This is deliberate and unavoidable:
    the flake lives in the agent's SQL GENERATION (a full model call), not
    in the deterministic recompute step, so nothing short of a fresh sample
    can plausibly change the outcome. The retry is narrowly scoped — it is
    only ever constructed by eval_gate for a question that (a) already
    scored correct and (b) failed citation resolution for EXACTLY the
    empty-touched-tables reason — never for a wrong answer, a REFUSE, or an
    `error: True` crash (those are filtered out before this factory is ever
    called; see eval_gate).

    The re-sampled attempt is re-scored from scratch (`_score_answer`) and
    its citation re-resolved (`_resolve_citation`) exactly as the original
    was. It is reported as "resolved" (non-empty touched_tables, the signal
    resolve_citation_with_retry checks) ONLY when the fresh sample is BOTH
    still correct AND its citation resolves — never on citation alone. This
    is what makes it impossible for the retry to mask a genuinely wrong
    answer: a fresh sample that answers incorrectly is reported as
    unresolved regardless of what its SQL touched, so it can never look like
    a pass.
    """
    state = {"call": 0}

    def _recompute(question_id):  # noqa: ARG001 - kept for interface parity with the generic primitive
        state["call"] += 1
        if state["call"] == 1:
            fresh, fresh_correct, cit = first_result, first_is_correct, first_citation
        else:
            try:
                fresh = agent_run_fn(
                    question, client=client, duckdb_path=duckdb_path, print_cost=False,
                )
            except SystemExit as exc:
                fresh = _error_agent_result(f"SystemExit during citation retry: {exc}")
            except Exception as exc:  # noqa: BLE001 - mirror eval_gate's own top-level guard
                fresh = _error_agent_result(f"citation retry crashed: {exc}")

            fresh_correct = _score_answer(fresh, entry)
            if fresh.get("refuse", False) or fresh.get("error", False):
                # The resample refused or crashed — nothing to resolve. This
                # already fails fresh_correct too (an entry with a non-REFUSE
                # expected_answer scores any refuse=True as False, and
                # error:True disqualifies unconditionally), so `resolved`
                # below is False either way; this branch just avoids handing
                # a None/refused SQL to _resolve_citation.
                cit = {"ok": False, "reason": "citation retry: agent refused or crashed on resample"}
            else:
                cit = _resolve_citation(
                    fresh, entry,
                    duckdb_path=duckdb_path,
                    citations_parquet=citations_parquet,
                    is_correct=fresh_correct,
                )

        resolved = bool(fresh_correct and cit.get("ok"))
        return {
            # A synthetic truthy/falsy marker for resolve_citation_with_retry's
            # own empty-check — NOT the real touched-tables set (which lives
            # inside `citation`/`_resolve_citation`'s own accounting and isn't
            # needed by anything downstream of this closure).
            "touched_tables": ["resolved"] if resolved else [],
            "result": fresh,
            "is_correct": fresh_correct,
            "citation": cit,
        }

    return _recompute


# ROADMAP #139 (code half, decided 2026-09-25): an eval run the PROVIDER
# refused is BLOCKED, not an accuracy failure. From 2026-09-18 until the
# owner's top-up the key answered HTTP 400 "credit balance is too low": every
# question came back ERROR at $0.00 and the gate printed "accuracy 0/48 < 44
# threshold" with `blocked: false` in the run record — a model failure the
# model never got to commit. The texts below are the Anthropic API's own
# credit / authentication / permission refusals (invalid_request_error's
# credit message, authentication_error, permission_error); a rate limit or a
# 5xx is NOT one of them — agent.run already retries those, and one that
# survives four attempts is a transport failure worth a FAIL.
_PROVIDER_BLOCK_RE = re.compile(
    r"credit balance is too low|authentication_error|invalid x-api-key"
    r"|permission_error|billing_error",
    re.IGNORECASE,
)
#: Anything shaped like an Anthropic key, scrubbed from recorded error text.
_API_KEY_RE = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")
_ERROR_TEXT_MAX = 300


def _recorded_error_text(exc: BaseException) -> str:
    """The exception's text as the run record keeps it: one line, bounded,
    and never a key (an SDK error echoing a header must not reach a JSON
    file under data/research/)."""
    text = " ".join(str(exc).split()) or type(exc).__name__
    return _API_KEY_RE.sub("sk-ant-…", text)[:_ERROR_TEXT_MAX]


def _refusals_and_other_errors(
    scores: list[dict],
) -> tuple[list[dict], list[dict], float]:
    """Split a run's ERRORED questions into (provider refusals, every other
    error) and return the run's spend — the one classification
    provider_block_reason and non_provider_error_clause both read.

    A question is "refused by the provider" when
      * its recorded `agent_error_text` carries the provider's credit / auth /
        permission refusal (_PROVIDER_BLOCK_RE) — recorded since 2026-09-25;
      * OR every question in the run is ERROR, the run spent $0.00 and the
        record kept NO error text — the shape of every record written
        2026-09-18..25, before the text was kept: no model call completed,
        so the run measured nothing. Once text is kept it is the evidence: an
        all-ERROR $0 run whose recorded errors are something else (a
        TypeError before the first API call) is the code's failure.
    Every other errored question is NOT a refusal: a crash with its own text,
    or (records before 2026-09-25) an error that kept no text in a run that
    is not the all-ERROR, $0 shape.
    """
    errored = [s for s in scores if s.get("agent_error")]
    spent = sum(
        float(s.get("cost_usd") or 0.0) + float(s.get("citation_retry_cost_usd") or 0.0)
        for s in scores
    )
    all_error_free = (
        bool(errored) and len(errored) == len(scores) and spent == 0.0
        and not any(s.get("agent_error_text") for s in errored)
    )
    if all_error_free:
        return errored, [], spent
    refused, other = [], []
    for s in errored:
        if _PROVIDER_BLOCK_RE.search(s.get("agent_error_text") or ""):
            refused.append(s)
        else:
            other.append(s)
    return refused, other, spent


#: How many non-provider errors non_provider_error_clause names by id.
_NAMED_ERRORS_MAX = 5


def non_provider_error_clause(run: dict) -> str | None:
    """The sentence naming a run's errors that are NOT provider refusals, or
    None when it has none (R-DEC-139b, 2026-09-26: "any crash keeps FAIL and
    is named"). eval_gate appends it to a FAIL's reason and
    cmd_verify_phase5 prints it, so a run that mixes a code crash with
    credit refusals says which questions crashed instead of reading as an
    accuracy score alone.

    Each named question carries its recorded error text, or "no error text
    recorded" for a record written before 2026-09-25 — such an error is
    called what the record shows (an error with no provider refusal on
    record), never a crash or a refusal it does not show.
    """
    scores = run.get("scores") or []
    refused, other, _spent = _refusals_and_other_errors(scores)
    if not other:
        return None
    named = []
    for s in other[:_NAMED_ERRORS_MAX]:
        text = " ".join((s.get("agent_error_text") or "").split())
        named.append(
            f"{s.get('id', '?')} ({text[:80] if text else 'no error text recorded'})"
        )
    more = len(other) - len(named)
    listing = ", ".join(named) + (f" and {more} more" if more else "")
    refused_clause = (
        f"; {len(refused)} other(s) were refused by the provider" if refused
        else ""
    )
    return (
        f"{len(other)} of {len(scores)} questions errored with no provider"
        f" refusal on record: {listing}{refused_clause} — an error the"
        " provider did not cause is the code's failure, so this run is a"
        " FAIL, not a provider block"
    )


def provider_block_reason(
    run: dict, *, threshold: int = ACCURACY_THRESHOLD,
) -> str | None:
    """Why this eval run is BLOCKED by the provider, or None when it is not.

    Reads the RUN RECORD (the dict eval_gate returns and cmd_verify_phase5
    writes to data/research/eval-runs/), so it can be applied to a stored
    record as well as a live one. Which errored questions count as "refused
    by the provider" is _refusals_and_other_errors' rule (credit / auth /
    permission text, or the all-ERROR, $0, no-text shape of the records
    written 2026-09-18..25).

    R-DEC-139b (controller ruling 2026-09-26, under the owner's delegation):
    BLOCKED only when the provider's refusals ALONE decide the verdict and no
    other failure occurred —
      * no errored question is anything but a provider refusal: an error the
        provider did not cause (a TypeError, or an error whose record kept no
        text outside the all-ERROR $0 shape) is the code's failure, so the
        run is a FAIL (non_provider_error_clause names the errors);
      * `correct < threshold <= correct + refused` — the answered questions
        have not reached the bar on their own, and the refused ones could
        still carry the run there. An answer scored WRONG is a measured
        answer: it counts against the bar through this inequality and does
        not by itself decide anything (R-DEC-139c, fix round 2: the
        2026-09-18 shape — 27 correct, 20 refused, 1 wrong — is BLOCKED
        once its refusals are on record). A wrong answer does not show a run
        would have failed: of the 36 stored runs that reached >= 44 correct
        (the 50 distinct eval-*.json records in data/research/eval-runs/
        across the repo's checkouts, read 2026-09-26), 26 carry at least one
        answer scored wrong. Their correct counts: 47/48 in 17 runs, 48/48
        in 8, 46/48 in 8, 45/48 in 2, 45/45 in 1 (a miss that is not a wrong
        answer is an ERROR row);
      * no answered question's citation failed to resolve — the 100%
        citation bar is already broken.
    Spend is not part of the rule: a credit balance runs out MID-run, after
    the questions before it were paid for (2026-09-18: 27 answered, then 20
    refused). The stage-1 rule (2026-09-25) required only one refusal text
    and `correct + refused >= threshold`, so a run mixing refusals with code
    crashes read BLOCKED and hid the crashes; this one cannot. Fix round 1
    also refused BLOCKED to any run with a wrong answer, which printed an
    accuracy FAIL for runs whose accuracy was never measured; that clause is
    gone (fix round 2).
    """
    scores = run.get("scores") or []
    if not scores:
        return None
    refused, other, spent = _refusals_and_other_errors(scores)
    if not refused or other:
        return None

    correct = sum(1 for s in scores if s.get("correct"))
    if correct >= threshold:
        # The answered questions reach the bar on their own: the refusals
        # decide nothing (eval_gate passes such a run on its citations).
        return None
    if correct + len(refused) < threshold:
        # Even every refused question answered correctly could not reach it:
        # the answered questions already decided the FAIL.
        return None
    if any(s.get("citation_resolved") is False for s in scores):
        return None

    wrong = len(scores) - correct - len(refused)
    cause = next(
        (s["agent_error_text"] for s in refused if s.get("agent_error_text")),
        None,
    )
    cause_clause = (
        f"the provider answered: {cause}" if cause
        else "the run record carries no error text (records written before"
             " 2026-09-25 did not keep it)"
    )
    return (
        f"eval run BLOCKED by the provider — {len(refused)} of {len(scores)}"
        f" questions never reached the model (ERROR, run spend ${spent:.2f});"
        f" {correct} answered correctly"
        + (f" and {wrong} wrong" if wrong else "")
        + f", so the {threshold}-question accuracy bar was not measured (the"
        f" run reaches it only if at least {threshold - correct} of the"
        f" {len(refused)} refused questions are answered correctly)."
        f" {cause_clause}. Fix the key or its credit and re-run:"
        " uv run python -m govbudget verify-phase5"
    )


def _refusal_phrase(refused: list[dict]) -> str:
    """The provider's own words for a refusal (the _PROVIDER_BLOCK_RE match
    in the first refused question that kept text), or "no error text
    recorded"."""
    for s in refused:
        m = _PROVIDER_BLOCK_RE.search(s.get("agent_error_text") or "")
        if m:
            return m.group(0)
    return "no error text recorded"


def provider_refusal_clause(
    run: dict, *, threshold: int = ACCURACY_THRESHOLD,
) -> str | None:
    """The sentence a FAIL carries when the provider refused some of its
    questions but the refusals do not decide the verdict (fix round 2).

    Without it such a run printed "accuracy 30/48 < 44 threshold" and nothing
    else, hiding that the provider had refused part of it. None when the run
    has no refusal, when it is a provider block (provider_block_reason is
    then the sentence), when a non-provider error occurred
    (non_provider_error_clause already counts the refusals beside it), or
    when the answered questions reach the bar on their own (no FAIL for
    this sentence to explain).
    """
    scores = run.get("scores") or []
    refused, other, _spent = _refusals_and_other_errors(scores)
    if not refused or other:
        return None
    if provider_block_reason(run, threshold=threshold) is not None:
        return None
    correct = sum(1 for s in scores if s.get("correct"))
    n = len(refused)
    if any(s.get("citation_resolved") is False for s in scores):
        why = ("an answered question's citation failed to resolve, so the"
               " 100% citation bar is already broken")
    elif correct + n < threshold:
        why = (f"even answered correctly they could not reach the"
               f" {threshold}-question bar ({correct} + {n} < {threshold})")
    else:
        return None
    return (
        f"{n} of {len(scores)} questions were refused by the provider"
        f" ({_refusal_phrase(refused)}); they do not decide this FAIL: {why}"
    )


#: Width of the per-question `error=` field cmd_verify_phase5 prints.
_ERROR_EXCERPT_WIDTH = 80


def _error_excerpt(text: str, width: int = _ERROR_EXCERPT_WIDTH) -> str:
    """A recorded error text as one console field: its first `width`
    characters — or, for a provider refusal the head would cut off, the
    window that starts at the refusal. The SDK's message front-loads
    "Error code: 400 - {'type': 'error', 'error': {'type':
    'invalid_request_error', '", so an 80-character head clip ended before
    "credit balance" (fix round 2)."""
    text = " ".join(text.split())
    m = _PROVIDER_BLOCK_RE.search(text)
    if m and m.end() > width:
        return "…" + text[m.start():m.start() + width]
    return text[:width]


def eval_gate(
    *,
    client=None,
    duckdb_path: Path | None = None,
    citations_parquet: Path | None = None,
) -> dict:
    """Run the analyst agent over all 48 eval questions.

    Returns:
        ok (bool)
        blocked (bool)  — True when ANTHROPIC_API_KEY is absent, when the
            agent exits mid-run, or when the provider refused enough of the
            run that its verdict was never measured (provider_block_reason,
            ROADMAP #139)
        block_cause (str) — present when blocked: "no_key" | "exit" |
            "provider"
        scores (list of dicts, one per question) — each also carries
            citation_retried (bool) / citation_retry_attempts (int | None) /
            citation_retry_cost_usd (float): backlog #36's bounded, recorded
            citation-resolution retry (see resolve_citation_with_retry).
        accuracy (int)  — number of correctly scored answers
        total (int)     — 48
        citation_ok (int)    — answered questions with resolved citations
        citation_total (int) — answered questions evaluated for citation
        citation_retry_count (int)          — questions that triggered a
            REAL paid agent resample (backlog #36)
        citation_retry_total_cost_usd (float) — API spend incurred by those
            resamples, on top of the base ~48-question run cost
        reason (str | None)  — set when BLOCKED or FAIL
    """
    from govbudget.common.anthropic_client import require_client
    from govbudget.analyst.agent import run as agent_run

    _NO_KEY_MSG = """\
eval_gate: ANTHROPIC_API_KEY is not set — the live eval run is BLOCKED.

Export a key and re-run:

    export ANTHROPIC_API_KEY=sk-ant-...
    uv run python -m govbudget verify-phase5

Nothing was run and nothing was spent. (~48 questions × ~8 turns ≈ $0.55 uncached.)"""

    # Check for client/key — do NOT call require_client yet (it exits)
    import os
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        return {
            "ok": False,
            "blocked": True,
            "block_cause": "no_key",
            "scores": [],
            "accuracy": 0,
            "total": 48,
            "citation_ok": 0,
            "citation_total": 0,
            "citation_retry_count": 0,
            "citation_retry_total_cost_usd": 0.0,
            "reason": _NO_KEY_MSG,
        }

    # Acquire client (exits if key absent and no fake client passed)
    real_client = require_client(client, message=_NO_KEY_MSG)

    entries = _load_yaml()
    scores: list[dict[str, Any]] = []
    correct = 0
    citation_ok = 0
    citation_total = 0
    citation_retry_count = 0
    citation_retry_total_cost_usd = 0.0

    for entry in entries:
        eid = entry["id"]
        question = entry["question"]
        expected = str(entry.get("expected_answer", ""))

        # Run the agent
        try:
            result = agent_run(
                question,
                client=real_client,
                duckdb_path=duckdb_path,
                print_cost=False,
            )
        except SystemExit as exc:
            # Key vanished mid-run
            return {
                "ok": False,
                "blocked": True,
                "block_cause": "exit",
                "scores": scores,
                "accuracy": correct,
                "total": len(entries),
                "citation_ok": citation_ok,
                "citation_total": citation_total,
                "citation_retry_count": citation_retry_count,
                "citation_retry_total_cost_usd": citation_retry_total_cost_usd,
                "reason": str(exc),
            }
        except Exception as exc:
            # `error` is the load-bearing flag: _score_answer returns False
            # for it unconditionally. `refuse` stays True only so the
            # citation-resolution branch below skips a run that produced no
            # SQL to resolve — it must never be read as the agent having
            # JUDGED the question unanswerable.
            result = {
                "answer": "ERROR",
                "error": True,
                "refuse": True,
                "refuse_reason_class": None,
                "sql": None,
                "citation_kind": "none",
                "citation": str(exc),
                "turns": 0,
                "cost_usd": 0.0,
                "touched_tables": set(),
                # ROADMAP #139: the cause travels into the run record, so a
                # stored all-ERROR run says WHY (provider_block_reason reads
                # it) instead of reading as a model that answered nothing.
                "error_text": _recorded_error_text(exc),
            }

        is_correct = _score_answer(result, entry)
        if is_correct:
            correct += 1

        # Citation resolution — only for answered (non-REFUSE) questions.
        # `error: True` runs are excluded automatically: the except-handler
        # above sets refuse=True on them too (commit e243f51), so this block
        # never sees a crash — and therefore the retry below never resamples
        # a question the agent never actually ran.
        cit_result: dict | None = None
        retried = False
        retry_attempts: int | None = None
        retry_cost_usd = 0.0
        if not result.get("refuse", False):
            citation_total += 1
            retry_attempts = 1
            cit_result = _resolve_citation(
                result,
                entry,
                duckdb_path=duckdb_path,
                citations_parquet=citations_parquet,
                is_correct=is_correct,
            )

            # Bounded, recorded retry (backlog #36). Gated on is_correct so
            # this can NEVER rescue a genuinely wrong answer — it only fires
            # for the documented flake shape: answer already scored correct,
            # citation failed for EXACTLY the empty-touched-tables reason
            # (literal/echo agent SQL), which is agent-sampling noise, not a
            # build defect. See _citation_retry_recompute's docstring for
            # why this must re-sample the agent (costs API money) rather
            # than re-running the same frozen SQL (a no-op — see
            # resolve_citation_with_retry's docstring).
            if is_correct and not cit_result["ok"] and cit_result["reason"] == _EMPTY_TOUCHED_REASON:
                recompute = _citation_retry_recompute(
                    question, entry,
                    agent_run_fn=agent_run,
                    client=real_client,
                    duckdb_path=duckdb_path,
                    citations_parquet=citations_parquet,
                    first_result=result,
                    first_is_correct=is_correct,
                    first_citation=cit_result,
                )
                retry_out = resolve_citation_with_retry(eid, recompute, max_attempts=2)
                retried = retry_out["retried"]
                retry_attempts = retry_out["attempts"]
                if retried:
                    # A real agent call happened (attempt 2) whether or not
                    # it ended up resolving — cost is incurred either way.
                    retry_cost_usd = retry_out["result"].get("cost_usd", 0.0)
                    citation_retry_count += 1
                    citation_retry_total_cost_usd += retry_cost_usd
                    if retry_out["touched_tables"]:
                        # Adopt the retry's CITATION outcome only — never its
                        # answer/correctness, which stay pinned to the
                        # original scoring so `correct` can never drift from
                        # what this score entry displays.
                        cit_result = retry_out["citation"]
                    # else: exhausted without resolving — cit_result (the
                    # ORIGINAL failure) stands; the gate still FAILS here.

            if cit_result["ok"]:
                citation_ok += 1

        scores.append({
            "id": eid,
            "question": question[:80],
            "expected": expected,
            "agent_answer": result.get("answer", ""),
            "agent_error": result.get("error", False),
            "agent_refuse": result.get("refuse", False),
            "agent_refuse_class": result.get("refuse_reason_class"),
            "correct": is_correct,
            "citation_kind": result.get("citation_kind"),
            "citation_resolved": cit_result["ok"] if cit_result else None,
            "citation_reason": cit_result["reason"] if cit_result else None,
            "citation_retried": retried,
            "citation_retry_attempts": retry_attempts,
            "citation_retry_cost_usd": retry_cost_usd,
            "turns": result.get("turns", 0),
            "cost_usd": result.get("cost_usd", 0.0),
            **({"agent_error_text": result["error_text"]}
               if result.get("error_text") else {}),
        })

    accuracy_ok = correct >= ACCURACY_THRESHOLD
    citation_ok_all = citation_total == 0 or citation_ok == citation_total

    # ROADMAP #139: a run the provider refused is BLOCKED with its cause — but
    # only while the refusals could have changed the verdict (see
    # provider_block_reason); a run that already failed on what it answered
    # falls through to the FAIL below unchanged.
    blocked_reason = provider_block_reason({"scores": scores})
    if blocked_reason is not None and not (accuracy_ok and citation_ok_all):
        return {
            "ok": False,
            "blocked": True,
            "block_cause": "provider",
            "scores": scores,
            "accuracy": correct,
            "total": len(entries),
            "citation_ok": citation_ok,
            "citation_total": citation_total,
            "citation_retry_count": citation_retry_count,
            "citation_retry_total_cost_usd": citation_retry_total_cost_usd,
            "reason": blocked_reason,
        }

    return {
        "ok": accuracy_ok and citation_ok_all,
        "blocked": False,
        "scores": scores,
        "accuracy": correct,
        "total": len(entries),
        "citation_ok": citation_ok,
        "citation_total": citation_total,
        # backlog #36: bounded, recorded citation-resolution retry. Non-zero
        # citation_retry_count means real API spend was incurred beyond the
        # 48-question base cost — see cmd_verify_phase5's printed disclosure.
        "citation_retry_count": citation_retry_count,
        "citation_retry_total_cost_usd": citation_retry_total_cost_usd,
        "reason": None if (accuracy_ok and citation_ok_all) else "; ".join(
            part for part in (
                f"accuracy {correct}/{len(entries)} < {ACCURACY_THRESHOLD} threshold"
                if not accuracy_ok
                else f"citation resolution {citation_ok}/{citation_total} < 100%",
                # R-DEC-139b: a FAIL that carries errors the provider did not
                # cause names them (None when there are none).
                non_provider_error_clause({"scores": scores}),
                # Fix round 2: a FAIL beside provider refusals that do not
                # decide it says so (None when there are none, and on the
                # mixed case the clause above already counts them).
                provider_refusal_clause({"scores": scores}),
            ) if part
        ),
    }


# ---------------------------------------------------------------------------
# Gate 3: Assembly gate
# ---------------------------------------------------------------------------


def assembly_gate(*, repo_root: Path | None = None) -> dict:
    """Subprocess each phase verifier and collect verdicts.

    Returns:
        ok (bool)
        blocked (bool)      — True if any gate is BLOCKED and none FAILed
        all_blocked_phases (list[str])
        results (list of dicts): phase, returncode, verdict, blocked, output_tail
    """
    root = repo_root or config.ROOT
    results: list[dict] = []
    any_fail = False
    blocked_phases: list[str] = []

    for phase_cmd in _ASSEMBLY_PHASES:
        proc = subprocess.run(
            ["uv", "run", "python", "-m", "govbudget", phase_cmd],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        full_output = proc.stdout + proc.stderr
        returncode = proc.returncode

        # Parse verdict from full output via regex
        m = _VERDICT_RE.search(full_output)
        if m:
            verdict = m.group(1).upper()
        else:
            # No verdict found — infer from returncode
            verdict = "PASS" if returncode == 0 else "FAIL"

        is_blocked = verdict == "BLOCKED"
        is_fail = verdict == "FAIL" or (returncode not in (0, 1, 2) and not is_blocked)

        # Also treat returncode == 1 with BLOCKED verdict as blocked
        if is_blocked:
            blocked_phases.append(phase_cmd)
        elif is_fail:
            any_fail = True

        results.append({
            "phase": phase_cmd,
            "returncode": returncode,
            "verdict": verdict,
            "blocked": is_blocked,
            "output_tail": full_output[-800:],  # keep last 800 chars
        })

    ok = not any_fail and not blocked_phases
    blocked = not any_fail and bool(blocked_phases)

    return {
        "ok": ok,
        "blocked": blocked,
        "all_blocked_phases": blocked_phases,
        "results": results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _compute_exit_code(*, fg_ok: bool, eg: dict, ag: dict) -> int:
    """Determine the exit code given gate results.

    Truth table:
      freshness FAIL                        → 1  (data stale, must fix first)
      eval FAIL (ran, accuracy below bar)   → 1  (regardless of assembly state)
      eval PASS + assembly FAIL             → 1  (assembly hard failure)
      eval PASS + assembly BLOCKED          → 2  (only key blocking remains)
      eval BLOCKED + assembly BLOCKED       → 2  (all blocks are key-related)
      eval BLOCKED + assembly PASS          → 2  (key blocks eval only)
      all PASS                              → 0

    The critical invariant: exit 2 ONLY when every non-green item is
    genuinely key-blocked — no key, or (ROADMAP #139) a key the provider
    refused, when the refusal left the verdict unmeasured
    (provider_block_reason decides; a run that failed on what it answered
    stays blocked=False).  If eval ran and failed (ok=False, blocked=False),
    that is a hard FAIL → exit 1, regardless of assembly state.
    """
    if not fg_ok:
        return 1

    eval_ran_and_failed = not eg.get("ok", False) and not eg.get("blocked", False)
    if eval_ran_and_failed:
        return 1

    assembly_hard_failed = not ag.get("ok", False) and not ag.get("blocked", False)
    if assembly_hard_failed:
        return 1

    all_green = eg.get("ok", False) and ag.get("ok", False)
    if all_green:
        return 0

    # Everything non-green is either blocked or already green → key-blocked
    return 2


def cmd_verify_phase5(args) -> None:  # noqa: ARG001
    """Verify phase 5: freshness gate + eval gate + assembly gate."""
    repo_root = Path(__file__).resolve().parents[2]
    duckdb_path = config.DUCKDB_PATH
    citations_parquet = repo_root / "data" / "site" / "citations" / "citations.parquet"

    print("=== verify-phase5 ===")
    print(f"repo root: {repo_root}")
    print()

    all_ok = True
    any_blocked = False

    # ── Gate 1: Freshness ───────────────────────────────────────────────────
    print("--- gate freshness ---")
    fg = freshness_gate(duckdb_path=duckdb_path)
    if fg["ok"]:
        print(f"gate freshness: {len(fg['ok_ids'])} answers current → PASS")
    else:
        for eid, expected, live in fg["stale"]:
            print(f"  STALE {eid}: expected={expected!r} live={live!r}")
        for eid, err in fg["errors"]:
            print(f"  ERROR {eid}: {err}")
        print("gate freshness: FAIL")
        all_ok = False
    print()

    # ── Gate 2: Eval ────────────────────────────────────────────────────────
    print("--- gate eval ---")
    eg = eval_gate(duckdb_path=duckdb_path, citations_parquet=citations_parquet)

    # Persist per-question results BEFORE any printing — a live eval run costs
    # real money and must never be lost to a reporting bug. A run the provider
    # blocked is persisted too (ROADMAP #139): it made the calls, and its
    # record is the evidence of the block. Only a run that never started (no
    # key: no scores) writes nothing.
    if eg["scores"]:
        runs_dir = config.RESEARCH_DIR / "eval-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_path = runs_dir / (
            f"eval-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        run_path.write_text(json.dumps(eg, indent=2, sort_keys=True, default=str))
        print(f"gate eval: per-question results -> {run_path}")

    # backlog #36 cost disclosure: a citation retry re-samples the agent
    # (see resolve_citation_with_retry / _citation_retry_recompute) — this
    # must be visible whenever it happens, not buried only in the artifact.
    if eg.get("citation_retry_count", 0) > 0:
        print(
            f"gate eval: citation retry — {eg['citation_retry_count']} question(s) "
            f"resampled the agent (+${eg['citation_retry_total_cost_usd']:.4f} API spend)"
        )

    if eg["blocked"]:
        print(f"gate eval: BLOCKED — {eg['reason'].splitlines()[0]}")
        any_blocked = True
        all_ok = False
    elif eg["ok"]:
        print(
            f"gate eval: accuracy {eg['accuracy']}/{eg['total']}, "
            f"citation {eg['citation_ok']}/{eg['citation_total']} → PASS"
        )
    else:
        # Print score details. NOTE: dict.get(k, '') returns None when the key
        # exists with a None value — use `or ''` for optional fields.
        for s in eg["scores"]:
            if not s["correct"] or (s["citation_resolved"] is False):
                # R-DEC-139b: an errored question shows its recorded cause
                # (a provider refusal from the refusal itself, fix round 2).
                err = (
                    f" error={_error_excerpt(s.get('agent_error_text') or '')!r}"
                    if s.get("agent_error") and s.get("agent_error_text") else ""
                )
                print(
                    f"  {s['id']}: correct={s['correct']} "
                    f"cite={s.get('citation_resolved')} "
                    f"answer={(s.get('agent_answer') or '')[:60]!r} "
                    f"({(s.get('citation_reason') or '')[:60]}){err}"
                )
        print(
            f"gate eval: accuracy {eg['accuracy']}/{eg['total']}, "
            f"citation {eg['citation_ok']}/{eg['citation_total']} → FAIL"
        )
        crash_clause = non_provider_error_clause(eg)
        if crash_clause:
            print(f"gate eval: {crash_clause}")
        refusal_clause = provider_refusal_clause(eg)
        if refusal_clause:
            print(f"gate eval: {refusal_clause}")
        all_ok = False
    print()

    # ── Gate 3: Assembly ────────────────────────────────────────────────────
    print("--- gate assembly ---")
    ag = assembly_gate(repo_root=repo_root)

    verdicts: list[str] = []
    for r in ag["results"]:
        status = r["verdict"]
        verdicts.append(f"  {r['phase']}: {status}")
        print(f"  {r['phase']}: {status}")

    if ag["ok"]:
        print("gate assembly: PASS")
    elif ag["blocked"]:
        print(f"gate assembly: BLOCKED ({', '.join(ag['all_blocked_phases'])})")
        any_blocked = True
        all_ok = False
    else:
        print("gate assembly: FAIL")
        all_ok = False
    print()

    # ── Summary ─────────────────────────────────────────────────────────────
    print("=== summary ===")
    print(f"  gate freshness: {'PASS' if fg['ok'] else 'FAIL'}")
    if eg["blocked"]:
        print("  gate eval:      BLOCKED")
    else:
        print(f"  gate eval:      {'PASS' if eg['ok'] else 'FAIL'}")
    if ag["ok"]:
        print("  gate assembly:  PASS")
    elif ag["blocked"]:
        print(f"  gate assembly:  BLOCKED ({', '.join(ag['all_blocked_phases'])})")
    else:
        print("  gate assembly:  FAIL")
    print()

    exit_code = _compute_exit_code(fg_ok=fg["ok"], eg=eg, ag=ag)

    if exit_code == 0:
        print("verify-phase5: PASS")
    elif exit_code == 2 and eg.get("block_cause") == "provider":
        # The key IS set; the provider refused it (ROADMAP #139). Telling the
        # operator to export a key would send them after the wrong fix.
        print(
            "verify-phase5: BLOCKED — the eval provider refused the run "
            "(credit, authentication or permission), so accuracy was not "
            "measured.\n"
            f"{eg['reason'].splitlines()[0]}"
        )
    elif exit_code == 2:
        print(
            "verify-phase5: BLOCKED — one or more gates require ANTHROPIC_API_KEY.\n"
            "To unblock: export ANTHROPIC_API_KEY=sk-ant-... && "
            "uv run python -m govbudget verify-phase5"
        )
    else:
        print("verify-phase5: FAIL")

    sys.exit(exit_code)
