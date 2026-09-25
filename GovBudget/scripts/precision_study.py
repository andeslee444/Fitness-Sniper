"""Held-out precision study for the published link tiers (ROADMAP #72, #79).

draw   : stratified random sample per method from PUBLISHED links, written as
         evidence packets. --rubric is REQUIRED: every packet carries the
         rubric it is to be judged under, the exact question that rubric
         asks, and the evidence an answer needs (award description, program
         title / mission narrative / project titles / lexicon names, lake
         facts).
load   : ingest adjudicator verdicts JSON -> link_precision_samples, stamped
         with the rubric they were judged under. --rubric is REQUIRED, and a
         sample_id never mixes rubrics.
report : precision per method under EACH rubric, counted under the tier each
         sampled link publishes under TODAY. Only rubric='attribution' is
         published (precision_by_method's default; export_site's twin), and
         a PINNED tier (below) prints at its pinned run, with the tier's
         latest run, when it differs, on its own line tagged NOT PUBLISHED.

RUBRICS (ROADMAP #79). A verdict is comparable only to a verdict that answered
the same question. The 2026-09-04 run judged four strata on program
ATTRIBUTION — did this award pay for this program — and one,
`account+subagency`, on whether the MECHANICAL rule had fired (account
097-0400, sub-agency DARPA, PIID prefix HR0011): every one of its 60 reasons
restates the rule. 60/60 against the second question was printed beside the
first as one "precision" figure until the final review caught it (f96344e5).
Migration 015 stamps every row with its rubric; the exporter and
precision_by_method read one rubric at a time; a stratum whose only verdicts
answer another question stays UNMEASURED on /methodology/ until it is
re-judged on attribution under a new sample_id.

LATEST RUN, PER METHOD (final review I1, refined for #79). A study run may
re-judge one stratum only. Each method's figure comes from the latest
sample_id that judged THAT method under the rubric; a re-measurement replaces
the number it corrects and never pools with it, and the other methods keep
their own latest run.

EXCEPT A PINNED TIER (2026-09-19, R-25b-1; mirrored here in the Task 26 fix
wave). `PINNED_SAMPLES` is export_site's `_PINNED_PRECISION_SAMPLES` — the
same object, imported, not a copy. It pins `announcement+lexicon` to the
2026-09-04 draw over the whole tier: the 2026-09-12 run is a draw over ONE
wave's links, and "latest run" would have made it the tier's published
figure. The export re-tallies a pinned tier at its pinned run alone (and
reports it UNMEASURED if that run judged nothing the tier still publishes);
`precision_by_method(pinned_samples=...)` does the same, and `report` passes
the pin for the published rubric.
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

import psycopg

from govbudget.export_site import _PINNED_PRECISION_SAMPLES

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("GOVBUDGET_PG_DSN", "postgresql://localhost/govbudget")
CONTRACTS_GLOB = str(ROOT / "data" / "parquet" / "contracts" / "fy=*" / "*.parquet")
LEXICON_PATH = ROOT / "data" / "research" / "lexicon" / "lexicon.jsonl"
PACKETS_DIR = ROOT / "data" / "research" / "precision"

# Draw strata. `fpds-ap+account` is kept so an old sample_id still reproduces,
# but the tier was withdrawn 2026-09-04 (zero rows) and draw_sample skips any
# stratum with no published rows, so a fresh draw never touches it.
METHODS = ("fpds-ap+account", "fpds-ap", "announcement+lexicon", "subaward+lexicon",
           "account+subagency")

#: Published tier -> the run its /methodology/ figure comes from. The
#: exporter's constant itself (see the module docstring), so the CLI and the
#: page can never pin different runs.
PINNED_SAMPLES = _PINNED_PRECISION_SAMPLES

#: rubric -> the question an adjudicator answers. The key is what
#: link_precision_samples.rubric stores (migration 015 CHECK constraint); the
#: text is copied verbatim into every packet so the adjudicator answers the
#: question the row will be published under and no other. Adding a rubric
#: means adding it here, to the CHECK, and to the sentence on /methodology/.
RUBRICS = {
    "attribution": (
        "Does this award execute this program element? Confirm ONLY if the award's "
        "own description, acquisition-program tag or subaward evidence names work "
        "that this program element's J-book narrative or project titles own. The "
        "appropriation account, the awarding sub-agency and the contract-number "
        "prefix are the linking RULE, not evidence: a reason that only restates "
        "them is not a verdict under this rubric. When the evidence is silent, "
        "refute."
    ),
    "rule-fired": (
        "Did the mechanical linking rule fire as recorded — same appropriation "
        "account, same sub-agency, expected contract-number prefix? (The question "
        "the 2026-09-04 account+subagency stratum was judged on. Kept for audit; "
        "never published as precision.)"
    ),
}


def _require_rubric(rubric) -> str:
    if rubric not in RUBRICS:
        raise ValueError(f"rubric must be one of {sorted(RUBRICS)}, got {rubric!r}")
    return rubric


def draw_sample(dsn: str, per_method: int = 60, seed: int = 20260904, *,
                rubric: str, methods=METHODS) -> list[dict]:
    """Stratified random draw of PUBLISHED (high/medium) links, `per_method`
    per stratum, deterministic in `seed`. Every packet is stamped with the
    rubric and its question.

    The picked rows are ordered by (piid, pe_bli) explicitly — sorting whole
    rows would compare a nullable rationale.
    """
    _require_rubric(rubric)
    rng = random.Random(seed)
    out: list[dict] = []
    with psycopg.connect(dsn) as pg:
        for m in methods:
            rows = pg.execute(
                "select award_piid, pe_bli, recipient_name, rationale from budget_line_awards"
                " where method=%s and confidence in ('high','medium')"
                " order by award_piid, pe_bli", (m,)).fetchall()
            if not rows:
                continue
            pick = rows if len(rows) <= per_method else rng.sample(rows, per_method)
            out += [{"method": m, "rubric": rubric, "question": RUBRICS[rubric],
                     "piid": r[0], "pe_bli": r[1], "recipient": r[2], "rationale": r[3]}
                    for r in sorted(pick, key=lambda r: (r[0], r[1]))]
    return out


def enrich_packets(packets: list[dict], dsn: str, contracts_glob: str = CONTRACTS_GLOB,
                   lexicon_path: Path = LEXICON_PATH) -> list[dict]:
    """Attach, in place, the evidence an ATTRIBUTION verdict needs.

    program: the line's title, its mission narrative, the distinct project
             titles the J-book lists under it, and the lexicon's `own` names.
    award:   the lake's view of the PIID — longest description, sub-agencies,
             offices, funding accounts, acquisition-program tags, NAICS/PSC,
             period of performance, total obligation, fiscal years present.
             When no parquet matches `contracts_glob` the packet says so in
             `award.lake` instead of carrying an empty award silently.
    """
    pes = sorted({p["pe_bli"] for p in packets})
    piids = sorted({p["piid"] for p in packets})
    program: dict[str, dict] = {}
    with psycopg.connect(dsn) as pg:
        for pe in pes:
            title = pg.execute(
                "select title from budget_lines where pe_bli=%s"
                " order by fiscal_year desc, id limit 1", (pe,)).fetchone()
            mission = pg.execute(
                "select body from detail_narratives where pe_bli=%s and kind='mission'"
                " and not superseded order by length(body) desc, id limit 1", (pe,)).fetchone()
            projects = pg.execute(
                "select distinct project_number, title from detail_narratives"
                " where pe_bli=%s and kind='accomplishment_planned_program'"
                " and not superseded and title is not null order by 1, 2 limit 80",
                (pe,)).fetchall()
            program[pe] = {
                "title": title[0] if title else None,
                "mission": mission[0][:2500] if mission and mission[0] else None,
                "projects": [{"number": n, "title": t} for n, t in projects],
                "lexicon_own": [],
            }
    if Path(lexicon_path).exists():
        with open(lexicon_path) as f:
            for line in f:
                d = json.loads(line)
                if d.get("pe_bli") in program and d.get("ownership") == "own":
                    names = program[d["pe_bli"]]["lexicon_own"]
                    if d["name"] not in names and len(names) < 80:
                        names.append(d["name"])

    award: dict[str, dict] = {}
    lake_note = None
    try:
        import duckdb
        lst = ",".join("'" + p.replace("'", "''") + "'" for p in piids)
        rows = duckdb.sql(f"""
            select award_id_piid,
                   arg_max(coalesce(transaction_description, ''),
                           length(coalesce(transaction_description, ''))),
                   arg_max(coalesce(prime_award_base_transaction_description, ''),
                           length(coalesce(prime_award_base_transaction_description, ''))),
                   list(distinct awarding_sub_agency_name),
                   list(distinct awarding_office_name),
                   list(distinct federal_accounts_funding_this_award),
                   list(distinct dod_acquisition_program_description),
                   any_value(naics_description),
                   any_value(product_or_service_code_description),
                   min(period_of_performance_start_date),
                   max(period_of_performance_current_end_date),
                   sum(try_cast(federal_action_obligation as double)),
                   list(distinct fy)
            from read_parquet('{contracts_glob}', union_by_name=true)
            where award_id_piid in ({lst})
            group by 1
        """).fetchall()
        for r in rows:
            clean = lambda xs: sorted(x for x in (xs or []) if x)  # noqa: E731
            award[r[0]] = {
                "description": r[1][:1500] or None,
                "base_description": (r[2][:1500] or None) if r[2] != r[1] else None,
                "sub_agencies": clean(r[3]),
                "offices": clean(r[4]),
                "accounts": clean(r[5]),
                "acquisition_programs": [a for a in clean(r[6]) if a != "NONE"],
                "naics": r[7],
                "psc": r[8],
                "pop_start": str(r[9]) if r[9] else None,
                "pop_end": str(r[10]) if r[10] else None,
                "obligation": round(r[11], 2) if r[11] is not None else None,
                "fiscal_years": sorted(int(x) for x in (r[12] or []) if x is not None),
            }
    except Exception as e:  # no parquet under the glob (fixture checkout), bad glob
        lake_note = f"no contracts parquet readable at {contracts_glob}: {type(e).__name__}: {e}"

    for p in packets:
        p["program"] = program[p["pe_bli"]]
        p["award"] = award.get(p["piid"]) or {
            "lake": lake_note or f"no row for PIID {p['piid']} in the contracts lake"
        }
    return packets


def load_verdicts(dsn: str, sample_id: str, verdicts_path: Path, *, rubric: str) -> int:
    """Upsert one run's verdicts, stamped with `rubric`.

    Refuses (before writing anything) when a verdict row names a different
    rubric, when a verdict is neither confirmed nor refuted, or when
    `sample_id` already holds verdicts under another rubric: a re-judgement
    under a new question is a NEW sample_id, never an overwrite of the audit
    record.
    """
    _require_rubric(rubric)
    v = json.load(open(verdicts_path))          # [{piid, pe_bli, method, verdict, reason}]
    for x in v:
        if x.get("rubric", rubric) != rubric:
            raise ValueError(
                f"{x['piid']}/{x['pe_bli']}: verdict file says rubric {x['rubric']!r},"
                f" load asked for {rubric!r}")
        if x["verdict"] not in ("confirmed", "refuted"):
            raise ValueError(f"{x['piid']}/{x['pe_bli']}: verdict must be confirmed|refuted,"
                             f" got {x['verdict']!r}")
    with psycopg.connect(dsn) as pg:
        n_other, other = pg.execute(
            "select count(*), min(rubric) from link_precision_samples"
            " where sample_id = %s and rubric <> %s", (sample_id, rubric)).fetchone()
        if n_other:
            raise ValueError(
                f"sample_id {sample_id!r} already holds {n_other} verdict(s) under rubric"
                f" {other!r}; a re-judgement under {rubric!r} is a new sample_id")
        pg.cursor().executemany(
            """insert into link_precision_samples
               (sample_id, award_piid, pe_bli, method, rubric, verdict, reason, adjudicated_at)
               values (%s,%s,%s,%s,%s,%s,%s, now())
               on conflict (sample_id, award_piid, pe_bli) do update set
                 verdict=excluded.verdict, reason=excluded.reason, adjudicated_at=now()""",
            [(sample_id, x["piid"], x["pe_bli"], x["method"], rubric, x["verdict"],
              x.get("reason")) for x in v])
        pg.commit()
    return len(v)


def precision_tally_sql(sample_id: str | None) -> str:
    """Twin of export_site._precision_tally_sql — export_site never imports
    scripts/, so the text is duplicated by hand;
    tests/test_export_site_link_precision.py asserts the two tallies agree on
    one fixture. Change both or neither.

    Per published method: confirmed / judged under ONE rubric, from the
    method's LATEST run (or the given run), counted under the method the link
    publishes under TODAY; rows the corpus no longer publishes at high/medium
    drop out of both numbers.
    """
    run_clause = "" if sample_id is None else "and s.sample_id = %(sample_id)s"
    return f"""
        with judged as (
            select s.sample_id, b.method, s.verdict, s.adjudicated_at
            from link_precision_samples s
            join budget_line_awards b
              on b.award_piid = s.award_piid and b.pe_bli = s.pe_bli
            where s.verdict is not null
              and s.rubric = %(rubric)s
              and b.confidence in ('high', 'medium')
              {run_clause}
        ),
        latest as (
            select method, max(sample_id) as sample_id from judged group by method
        )
        select j.method, j.sample_id,
               count(*) filter (where j.verdict = 'confirmed') as confirmed,
               count(*) as sampled,
               max(j.adjudicated_at) as judged_at
        from judged j
        join latest l on l.method = j.method and l.sample_id = j.sample_id
        group by j.method, j.sample_id
        order by j.method
    """


def precision_runs_by_method(dsn: str, sample_id: str | None = None, *,
                             rubric: str = "attribution",
                             pinned_samples: dict[str, str] | None = None,
                             ) -> dict[str, tuple[str, int, int]]:
    """{method: (sample_id, confirmed, judged)} under one rubric.

    `pinned_samples` maps a method to the run its figure must come from, the
    way export_site._link_precision_block takes it: the method is re-tallied
    against that run alone and, if the run judged nothing the method still
    publishes, it is dropped (the export names it unmeasured) — never a
    fallback to the latest run.
    """
    _require_rubric(rubric)

    def _tally(pg, run: str | None) -> dict[str, tuple[str, int, int]]:
        rows = pg.execute(precision_tally_sql(run),
                          {"rubric": rubric, "sample_id": run}).fetchall()
        return {m: (sid, c, n) for m, sid, c, n, _judged in rows}

    with psycopg.connect(dsn) as pg:
        tally = _tally(pg, sample_id)
        for method, pinned_run in (pinned_samples or {}).items():
            tally.pop(method, None)
            pinned = _tally(pg, pinned_run).get(method)
            if pinned is not None:
                tally[method] = pinned
    return tally


def precision_by_method(dsn: str, sample_id: str | None = None, *,
                        rubric: str = "attribution",
                        pinned_samples: dict[str, str] | None = None,
                        ) -> dict[str, tuple[int, int]]:
    """{method: (confirmed, judged)} under one rubric (pinned as asked)."""
    return {m: (c, n) for m, (_sid, c, n) in precision_runs_by_method(
        dsn, sample_id, rubric=rubric, pinned_samples=pinned_samples).items()}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    draw = sub.add_parser("draw", help="stratified draw -> evidence packets")
    draw.add_argument("--rubric", required=True, choices=sorted(RUBRICS))
    draw.add_argument("--sample-id", required=True,
                      help="e.g. 2026-09-05; names the packets file")
    draw.add_argument("--methods", default=",".join(METHODS), help="comma-separated strata")
    draw.add_argument("--per-method", type=int, default=60)
    draw.add_argument("--seed", type=int, default=20260904)
    draw.add_argument("--no-enrich", action="store_true", help="bare packets (old shape)")
    draw.add_argument("--out", type=Path,
                      help=f"default {PACKETS_DIR}/packets_<sample-id>_<rubric>.json")

    load = sub.add_parser("load", help="verdicts JSON -> link_precision_samples")
    load.add_argument("--rubric", required=True, choices=sorted(RUBRICS))
    load.add_argument("--sample-id", required=True)
    load.add_argument("--verdicts", required=True, type=Path)

    report = sub.add_parser("report", help="audit view: every rubric, every stratum")
    report.add_argument("--sample-id")

    args = ap.parse_args(argv)
    if args.cmd == "draw":
        methods = tuple(m.strip() for m in args.methods.split(",") if m.strip())
        packets = draw_sample(DSN, per_method=args.per_method, seed=args.seed,
                              rubric=args.rubric, methods=methods)
        if not args.no_enrich:
            enrich_packets(packets, DSN)
        out = args.out or PACKETS_DIR / f"packets_{args.sample_id}_{args.rubric}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        json.dump(packets, open(out, "w"), indent=1, ensure_ascii=False)
        print(f"{len(packets)} packets (rubric={args.rubric}, seed={args.seed}) -> {out}")
    elif args.cmd == "load":
        n = load_verdicts(DSN, args.sample_id, args.verdicts, rubric=args.rubric)
        print(f"loaded {n} verdicts into {args.sample_id} under rubric={args.rubric}")
    elif args.cmd == "report":
        # AUDIT view: every rubric. Only 'attribution' is published; the rest
        # are marked so an operator never mistakes them for a page figure.
        # Counts are over PUBLISHED links, so a stratum's total can be below
        # the number drawn (links deleted or demoted since the draw).
        #
        # Without --sample-id the attribution block is the PUBLISHED view:
        # a pinned tier prints at its pinned run (as the export publishes it)
        # and the tier's latest run, when it differs from the pin, prints on
        # its own tagged line. With --sample-id every figure is that one
        # run's, pins not applied.
        def _line(m: str, sid: str, c: int, n: int, note: str = "") -> str:
            return f"  {m:<24} {c}/{n} = {100 * c / max(n, 1):.1f}%  ({sid}){note}"

        for rubric in sorted(RUBRICS):
            published = rubric == "attribution"
            tag = "" if published else \
                "  [NOT PUBLISHED — rubric answers a different question]"
            pins = PINNED_SAMPLES if published and not args.sample_id else {}
            print(f"## rubric={rubric}{tag}")
            figures = precision_runs_by_method(DSN, args.sample_id, rubric=rubric,
                                               pinned_samples=pins)
            for m, (sid, c, n) in sorted(figures.items()):
                print(_line(m, sid, c, n, "  [pinned]" if m in pins else ""))
            if not pins:
                continue
            latest = precision_runs_by_method(DSN, args.sample_id, rubric=rubric)
            for m, run in sorted(pins.items()):
                if m not in figures:
                    print(f"  {m:<24} UNMEASURED — pinned run {run} judged no link"
                          " this tier still publishes")
                if m in latest and latest[m][0] != run:
                    sid, c, n = latest[m]
                    print(_line(m, sid, c, n,
                                f"  [NOT PUBLISHED — latest run; the published"
                                f" figure is pinned to {run}]"))


if __name__ == "__main__":
    main(sys.argv[1:])
