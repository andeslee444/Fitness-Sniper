# Public text-to-SQL analyst surface — scoping note

**Date:** 2026-09-10
**Status:** SCOPING ONLY — no decision taken, no design beyond the options below
**Filed as:** ROADMAP backlog (the "Public text-to-SQL analyst surface" entry)

---

## Context

`docs/superpowers/specs/2026-06-11-phase5b-product-surface-design.md:109-111`
defers a "public text-to-SQL endpoint (analyst agent stays an internal CLI —
the paid-analyst surface comes after launch)", and the ledger's Post-launch row
(`ROADMAP.md:35`) still lists it. The engine, unlike the surface, is real and
already gated:

- `python -m govbudget analyst "<question>"` (`src/govbudget/cli.py:2647`) runs
  a manual tool loop on `MODEL = "claude-sonnet-4-6"`
  (`src/govbudget/analyst/agent.py:40`) with `MAX_TURNS = 8` (`:47`), the final
  turn forced to `submit_answer` (`:239-240`).
- The SQL tool accepts exactly one statement, which must start with SELECT or
  WITH (`_ALLOWED_STARTS`, `src/govbudget/analyst/sql_tool.py:83`), and caps
  results at `ROW_CAP = 200` / `TIMEOUT_SECONDS = 30` (`:85-86`). It opens
  DuckDB `read_only=True` (`:176`), registers `data/parquet` as the only
  readable filesystem prefix (`SET allowed_directories`, `:191`) and disables
  all other external access (`SET enable_external_access = false`, `:196`).
- It is exercised by the `verify-phase5` eval gate over 48 questions including
  5 REFUSE cases (`evals/phase5_questions.yaml`).

Measured cost, from the newest recorded run
(`data/research/eval-runs/eval-20260901T055645Z.json`, 2026-09-01, 48
questions): **$0.8471 total, $0.0176 mean, $0.0120 median, $0.1297 worst, 2.6
turns mean**. That run scored `accuracy 48/48` but `citation_ok 42/43` and
therefore `ok: false` ("citation resolution 42/43 < 100%") — the single most
important number in this note, and the reason it is not a small feature.

## Options

**A. Keep it internal (status quo).** Cost: zero. The agent stays a
maintainer's tool and an eval harness.

**B. Publish the answers, not the engine.** Render the eval set as a static
"asked and answered" page: each question, its answer, its SQL and its citation,
regenerated at build time from the same harness. Cost: hours. No runtime, no
spend per visitor, no abuse surface, and every published answer went through
the citation gate before it was a byte on the page.

**C. Public endpoint.** One serverless function holding `ANTHROPIC_API_KEY`, a
per-IP rate limit, a hard daily budget, and a queryable copy of the parquet
warehouse the function can reach. Cost at the measured mean: 1,000
questions/day ≈ **$18/day ≈ $530/month**, with a worst-case question 7× the
mean and no upper bound on how adversarially someone asks. Plus the operating
burden of a runtime the project does not have today.

**D. Gated behind accounts.** C, metered per user — which makes this entry a
dependent of the accounts decision
(`docs/superpowers/specs/2026-09-10-accounts-alerts-tier-scoping.md`), not an
independent one.

## Risks

- **Cited-or-absent versus generated prose.** Every number on this site is
  rendered from an artifact a gate inspected. A live answer is a number nobody
  saw before the reader did, and the newest eval run resolved 42 of 43
  citations — a 97.7% citation rate is a gate failure internally and would be a
  published falsehood externally.
- **Prompt injection through the question box.** The SQL tool is read-only and
  prefix-confined, so the blast radius is the *answer text*, not the warehouse
  — but an answer is the product.
- **Refusals must hold for strangers.** The refuse classes were tuned against 5
  curated cases (`evals/phase5_questions.yaml`), not against people trying.
- **Cost is unbounded by construction** without a per-IP and per-day cap that
  fails closed.

## The open decision

**May this site publish a number that no gate saw before it was rendered?**

- *No* → take Option B (or A) and say on `/coverage/` that the analyst is an
  internal tool whose answers are published only after the citation gate.
- *Yes* → C or D, and then the citation-resolution floor (100%, per the eval
  gate) has to be enforced **at answer time**, refusing to display an answer
  whose citation does not resolve — not merely measured in a nightly eval.
