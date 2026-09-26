"""Backfill the announcement path's RECORDED review outcomes into
announcement_link_reviews (ROADMAP #110, record half; decided 2026-09-25 under
the owner's delegation: "unrecorded review is not evidence"; refined by the
stage-1 follow-up ruling R-DEC-110, 2026-09-26).

/methodology/ says every announcement candidate is judged by an agent reviewer
and challenged by an independent adversarial reviewer. That review lived only
in the wave files on disk; this script puts every review RECORD those files
hold into Postgres, one row per (crosswalk link of the reviewed pair, record),
so the mart can gate a high announcement link on it (dbt source
jbook_announcement_link_reviews, exported by `jbooks export-facts`).

What each wave recorded per link (inspected 2026-09-25/26), and the row kind:

  wave4_verdicts/chunk_*.json  -> record_kind 'verdict_pair'
      per proposal: the reviewer's `verdict` (link / weak / wrong) and, for
      `link`, both refute lenses (`refute_a`, `refute_b`, each {refuted,
      reason}), the announcement it read (article_id) and the paragraph
      (record_index). EVERY proposal is a record: a 'weak' / 'wrong' is the
      reviewer's recorded rejection, and it never reached the lenses
      (adversarial 'not_run'); a 'link' no lens answered is 'not_run' too.
  wave1_result.json .. wave3_result.json  `surviving` -> 'survivor_list'
      {piid, pe_bli, reason}: the pair the reviewer proposed as a 'link' and
      the refuter did not refute (R-DEC-110: a survivor list IS a recorded
      review of both). reviewer 'link', adversarial 'upheld', reason kept.
  wave1_result.json, wave2_result.json  `refutations_sample` -> 'refutation_sample'
      {piid, pe_bli, refuted: true, reason}: a proposed 'link' the refuter
      refuted. reviewer 'link', adversarial 'refuted'. A 40-entry SAMPLE per
      wave; the rest of waves 1-2's refutations were recorded only as counts.
  wave4_result.json
      the collection step's survivors and counters — its per-link record IS
      the verdict files, so it adds no row (no double count).
  wave*_chunks/, llm_chunks/, candidates_llm.jsonl
      the INPUT packets — no outcome. A wave<N>_chunks packet names the
      article a wave 1-3 list entry was judged on: exactly one packet per
      (pair, wave) on 2026-09-26, so that packet's article_id is recorded
      (article_source 'wave_packet'); none, or more than one, records NULL.

No wave file names an exhibit or a fiscal year — the loader stamps them — so a
record of (award_piid, pe_bli) is attached to EVERY budget_line_awards row of
that pair (on 2026-09-26 each reviewed pair held exactly one row). A record
whose pair holds no row is counted and dropped (the table is per link).

The adversarial verdict of a verdict pair follows the wave-4 rubric
(scripts/mine_announcement_residue.py): 'upheld' when every lens returned
refuted=false, 'refuted' when any lens returned refuted=true, 'incomplete' when
none refuted but a lens is missing or not a JSON boolean. The wave-4 collector
kept an 'incomplete' pair out of its survivors; the GRADING rule reads it as
neither an uphold nor a refutation (R-DEC-INCOMPLETE, 2026-09-26: it never
binds as a refutation of a cited article, and alone it demotes as
'announcement_review_incomplete'). reviewed_at is NULL: no wave file carries a
review timestamp.

SCOPE (fix round 2, 2026-09-26). The records are the announcement PIPELINE's
own review records — the wave files above — and nothing else. The held-out
precision study (Postgres link_precision_samples, judged per sampled link) is
NOT read, by design: it measures the published tiers, and feeding its
verdicts back into the grading would bias the precision figure it publishes.
Measured read-only 2026-09-26: 10 of the 1,056 high announcement links that
stay high carry a 'refuted' attribution verdict in that study (samples
2026-09-04: 3, 2026-09-12: 7), each judged on a packet that names the article
their card cites — so "no high link carries a recorded refutation of its
cited article" is true of the pipeline's records only, not of every record on
disk.

ORDER (R-DEC-LOADER): migrate -> load_announcement_links -> THIS -> jbooks
export-facts -> dbt. The loader rebuilds the links and their source rows this
backfill attaches to and compares against; export-facts refuses a table
recorded before the loader's last run.

The table is REBUILT on every run (delete + insert in one transaction): it is a
derived copy of committed files, and a record whose file or link went away must
not linger.

Usage: uv run python scripts/backfill_announcement_link_reviews.py [--dry-run]

--dry-run reads Postgres read-only and prints what would be written, the
coverage of the announcement+lexicon links Postgres holds, and — when the
DuckDB warehouse can be opened read-only — the coverage of the high
announcement links fct_budget_to_awards publishes.
"""
import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import psycopg

from govbudget import config

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "research" / "announcements"
VERDICT_DIR = ANN / "wave4_verdicts"
#: The waves whose result file is a pair-level list (R-DEC-110). Wave 4's
#: per-link record is its verdict files.
LIST_WAVES = (1, 2, 3)
# The database the exporter reads: config.PG_DSN honours GOVBUDGET_PG_DSN and
# the gitignored .env (tests/test_loader_dsn.py).
DSN = config.PG_DSN
METHOD = "announcement+lexicon"
REVIEWER_VERDICTS = ("link", "weak", "wrong")

#: announcement_link_reviews' columns in the order this script writes them
#: (migration 018; recorded_at is the table's own default).
COLUMNS = (
    "award_piid", "pe_bli", "exhibit", "fiscal_year", "record_kind",
    "reviewer_verdict", "adversarial_verdict", "adversarial_lenses_passed",
    "upholds", "article_id", "article_source", "record_index", "entry_index",
    "cites_reviewed_article", "reason", "reviewed_at", "source_file",
)
_C = {name: i for i, name in enumerate(COLUMNS)}


@dataclass(frozen=True)
class ReviewRecord:
    """One review of one (award, PE) pair, as a wave file recorded it."""

    piid: str
    pe_bli: str
    record_kind: str              # verdict_pair | survivor_list | refutation_sample
    reviewer_verdict: str         # link | weak | wrong
    adversarial_verdict: str      # upheld | refuted | incomplete | not_run
    lenses_passed: int | None     # verdict pairs whose lenses ran; else None
    article_id: str | None
    article_source: str | None    # verdict_file | wave_packet | None
    record_index: int | None      # the announcement paragraph (verdict pairs)
    entry_index: int              # position in the source file's list
    reason: str | None            # a list entry's own reason; None for pairs
    source_file: str              # repo-relative


def lens_outcome(lens_a, lens_b) -> tuple[str, int] | None:
    """(adversarial_verdict, lenses_passed) from the two refute lenses, or None
    when neither lens recorded a verdict (the lenses never ran).

    A lens "recorded a verdict" when it is a dict carrying a `refuted` key.
    Only a JSON boolean false clears a lens; a true refutes; anything else
    (missing lens, non-boolean) leaves the outcome 'incomplete' unless another
    lens refuted. 'incomplete' is not a refutation (R-DEC-INCOMPLETE): the
    grading reads it as neither an uphold nor a refutation (classify()).
    """
    lenses = [x for x in (lens_a, lens_b)
              if isinstance(x, dict) and "refuted" in x]
    if not lenses:
        return None
    values = [x.get("refuted") if isinstance(x, dict) else None
              for x in (lens_a, lens_b)]
    passed = sum(1 for v in values if v is False)
    if any(v is True for v in values):
        return "refuted", passed
    if passed == 2:
        return "upheld", passed
    return "incomplete", passed


def _record_index(value) -> int | None:
    """The collector's own coercion: an int, or a string of digits."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _clean(value) -> str | None:
    """A packet field, or None when absent/blank/the string 'None' — the
    wave-3 (subaward) packets carry the STRING 'None' for article_id, as
    load_announcement_links._packet_value documents."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s and s != "None" else None


def _rel(path: Path, root: Path) -> str:
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def read_verdict_files(verdict_dir: Path, root: Path = ROOT
                       ) -> tuple[list[ReviewRecord], dict[str, int]]:
    """Every wave-4 proposal in verdict_dir/chunk_*.json, as a verdict_pair.

    Counted and skipped (never guessed): a file with no `proposals` list (a
    crashed lens), a proposal that is not an object, a reviewer verdict
    outside link/weak/wrong, a proposal with no piid / pe_bli / article_id,
    and one with no usable record_index.
    """
    counts = {"files": 0, "malformed_file": 0, "not_a_proposal": 0,
              "invalid_verdict": 0, "missing_ids": 0, "no_record_index": 0,
              "recorded": 0, "link_with_lens": 0, "link_without_lens": 0,
              "rejection": 0}
    records: list[ReviewRecord] = []
    for path in sorted(Path(verdict_dir).glob("chunk_*.json")):
        counts["files"] += 1
        body = json.loads(path.read_text())
        proposals = body.get("proposals") if isinstance(body, dict) else None
        if not isinstance(proposals, list):
            counts["malformed_file"] += 1
            continue
        rel = _rel(path, root)
        for entry, prop in enumerate(proposals):
            if not isinstance(prop, dict):
                counts["not_a_proposal"] += 1
                continue
            verdict = prop.get("verdict")
            if verdict not in REVIEWER_VERDICTS:
                counts["invalid_verdict"] += 1
                continue
            piid = prop.get("piid")
            pe = str(prop.get("pe_bli") or "").strip()
            article = _clean(prop.get("article_id"))
            if not isinstance(piid, str) or not piid or not pe or article is None:
                counts["missing_ids"] += 1
                continue
            index = _record_index(prop.get("record_index"))
            if index is None:
                counts["no_record_index"] += 1
                continue
            outcome = (lens_outcome(prop.get("refute_a"), prop.get("refute_b"))
                       if verdict == "link" else None)
            if verdict != "link":
                counts["rejection"] += 1
            elif outcome is None:
                counts["link_without_lens"] += 1
            else:
                counts["link_with_lens"] += 1
            adv, lenses = outcome if outcome else ("not_run", None)
            records.append(ReviewRecord(
                piid, pe, "verdict_pair", verdict, adv, lenses, article,
                "verdict_file", index, entry, None, rel))
            counts["recorded"] += 1
    return records, counts


def _wave_packets(chunks: Path) -> dict[tuple[str, str], list[str | None]]:
    """(piid, pe_bli) -> the article ids of every packet the wave triaged for
    the pair (None for a packet that names no article)."""
    out: dict[tuple[str, str], list[str | None]] = {}
    for f in sorted(chunks.glob("chunk_*.json")):
        for p in json.loads(f.read_text()):
            if isinstance(p, dict) and p.get("piid") and p.get("pe_bli"):
                out.setdefault((p["piid"], str(p["pe_bli"]).strip()), []).append(
                    _clean(p.get("article_id")))
    return out


def read_result_files(ann: Path = ANN, root: Path = ROOT, waves=LIST_WAVES
                      ) -> tuple[list[ReviewRecord], dict[str, int]]:
    """The wave 1-3 result files' pair-level records (R-DEC-110):
    `surviving` -> survivor_list (link + upheld), `refutations_sample` ->
    refutation_sample (link + refuted), each with the article of the one
    packet its wave triaged for the pair.

    A missing wave<N>_result.json or wave<N>_chunks/ is REFUSED: silently
    reading fewer waves would record every survivor of the missing one as
    unreviewed."""
    counts = {"survivor_list": 0, "refutation_sample": 0, "not_an_entry": 0,
              "refutation_not_true": 0, "no_packet": 0,
              "packet_without_article": 0, "ambiguous_packet": 0}
    records: list[ReviewRecord] = []
    for n in waves:
        path = Path(ann) / f"wave{n}_result.json"
        chunks = Path(ann) / f"wave{n}_chunks"
        if not path.is_file():
            raise SystemExit(f"{path.name}: not found in {ann} — every pair it"
                             " records would be backfilled as unreviewed")
        if not chunks.is_dir():
            raise SystemExit(f"{path.name}: no {chunks.name}/ in {ann} — the"
                             " articles its pairs were judged on are unknown")
        body = json.loads(path.read_text())
        packets = _wave_packets(chunks)
        rel = _rel(path, root)
        lists = (("survivor_list", "upheld", body.get("surviving") or []),
                 ("refutation_sample", "refuted", body.get("refutations_sample") or []))
        for kind, adv, entries in lists:
            for entry, e in enumerate(entries):
                if not (isinstance(e, dict) and isinstance(e.get("piid"), str)
                        and e.get("piid") and str(e.get("pe_bli") or "").strip()):
                    counts["not_an_entry"] += 1
                    continue
                if kind == "refutation_sample" and e.get("refuted") is not True:
                    counts["refutation_not_true"] += 1
                    continue
                pe = str(e["pe_bli"]).strip()
                arts = set(packets.get((e["piid"], pe), []))
                article = None
                if not arts:
                    counts["no_packet"] += 1
                elif len(arts) > 1:
                    counts["ambiguous_packet"] += 1
                elif next(iter(arts)) is None:
                    counts["packet_without_article"] += 1
                else:
                    article = next(iter(arts))
                reason = e.get("reason")
                records.append(ReviewRecord(
                    e["piid"], pe, kind, "link", adv, None, article,
                    "wave_packet" if article else None, None, entry,
                    reason if isinstance(reason, str) else None, rel))
                counts[kind] += 1
    return records, counts


def review_rows(records, links: dict, cited: dict) -> tuple[list[tuple], dict]:
    """announcement_link_reviews rows (COLUMNS order) for every record whose
    pair holds at least one budget_line_awards row.

    links:  (award_piid, pe_bli) -> [(exhibit, fiscal_year), ...] — EVERY
            budget_line_awards row of the pair, whatever its method
    cited:  (award_piid, pe_bli) -> {article_id} its announcement
            award_link_sources rows cite
    """
    rows: list[tuple] = []
    seen: set[tuple] = set()
    counts = {"no_link": 0, "duplicate": 0}
    for r in records:
        idents = links.get((r.piid, r.pe_bli))
        if not idents:
            counts["no_link"] += 1
            continue
        for exhibit, fy in sorted(set(idents)):
            key = (r.piid, r.pe_bli, exhibit, int(fy), r.source_file,
                   r.record_kind, r.entry_index)
            if key in seen:
                counts["duplicate"] += 1
                continue
            seen.add(key)
            upholds = r.reviewer_verdict == "link" and r.adversarial_verdict == "upheld"
            cites = (None if r.article_id is None
                     else r.article_id in cited.get((r.piid, r.pe_bli), set()))
            rows.append((r.piid, r.pe_bli, exhibit, int(fy), r.record_kind,
                         r.reviewer_verdict, r.adversarial_verdict,
                         r.lenses_passed, upholds, r.article_id,
                         r.article_source, r.record_index, r.entry_index,
                         cites, r.reason, None, r.source_file))
    return rows, counts


def _names_article(row) -> bool:
    """The mart's test: article_id neither NULL nor blank."""
    return row[_C["article_id"]] is not None and bool(str(row[_C["article_id"]]).strip())


def _binds(row) -> bool:
    """Does this record speak about the article the link's card cites? The
    mart's rule (dbt/models/audit/audit_link_grading.sql, review_records):
    a record naming no article binds to the pair, and so does one whose
    article match is unknown (cites_reviewed_article NULL) — read against the
    card, never wider."""
    if not _names_article(row):
        return True
    return row[_C["cites_reviewed_article"]] is not False


def classify(link_rows) -> dict:
    """What the review rows of ONE link record, in R-DEC-110's terms — the
    mart's predicates, one for one (R-DEC-INCOMPLETE, 2026-09-26: "one rule
    everywhere"; tests/test_backfill_announcement_link_reviews.py runs the
    committed model against this function):

      upholds  reviewer 'link' AND adversarial 'upheld'
      refutes  adversarial 'refuted' — ONLY that: an 'incomplete' read (a lens
               missing or not a JSON boolean) is neither an uphold nor a
               refutation, and never binds as a refutation of the cited
               article; a 'not_run' decides nothing either
      rejects  reviewer 'weak' / 'wrong'
      binds    see _binds()
    """
    upheld_kinds = {r[_C["record_kind"]] for r in link_rows if r[_C["upholds"]]}
    refutes = [r for r in link_rows if r[_C["adversarial_verdict"]] == "refuted"]
    rejects = [r for r in link_rows
               if r[_C["reviewer_verdict"]] in ("weak", "wrong")]
    return {
        "upheld_kinds": upheld_kinds,
        "refuted_cited": any(r[_C["cites_reviewed_article"]] is True for r in refutes),
        "rejected_cited": any(r[_C["cites_reviewed_article"]] is True for r in rejects),
        "refuted_binding": any(_binds(r) for r in refutes),
        "rejected_binding": any(_binds(r) for r in rejects),
        "contrary_without_article": any(
            not _names_article(r) for r in refutes + rejects),
        "refuted_any": bool(refutes),
        "rejected_any": bool(rejects),
        "any": bool(link_rows),
    }


def rule_outcome(c: dict) -> str:
    """R-DEC-110 + R-DEC-INCOMPLETE, as the mart applies them: high iff an
    upholding record exists AND no binding reviewer rejection / adversarial
    refutation exists (_binds: it names the article the link cites, or names
    none); otherwise medium with the reason that is TRUE of the link, first
    match wins — a binding refutation, a binding rejection, then (with no
    upholding record) any refutation, any rejection, 'review_incomplete' when
    records exist but none upholds, refutes or rejects (an 'incomplete' read,
    or a 'link' whose lenses never ran), and 'review_unrecorded' only when
    the link has no record at all. The mart applies the rule (dbt); this is
    the backfill's measurement of it."""
    if c["refuted_binding"]:
        return "review_refuted"
    if c["rejected_binding"]:
        return "reviewer_rejected"
    if c["upheld_kinds"]:
        return "stays high"
    if c["refuted_any"]:
        return "review_refuted"
    if c["rejected_any"]:
        return "reviewer_rejected"
    if c["any"]:
        return "review_incomplete"
    return "review_unrecorded"


def coverage(rows, published) -> dict[str, int]:
    """Classify every published link identity by the review rows it carries.
    'refuted/rejected on the cited article' count records whose article IS
    the card's; 'contrary record naming no article' counts links carrying a
    refutation or rejection that names none (it binds to the pair — _binds);
    the 'rule:' counts apply rule_outcome, the mart's rule."""
    by_link: dict[tuple, list[tuple]] = {}
    for row in rows:
        by_link.setdefault(tuple(row[:4]), []).append(row)
    out = {"total": 0,
           "upheld: verdict_pair only": 0, "upheld: survivor_list only": 0,
           "upheld: both kinds": 0, "no upholding record": 0,
           "refuted on the cited article": 0, "rejected on the cited article": 0,
           "contrary record naming no article": 0,
           "no record at all": 0,
           "rule: stays high": 0, "rule: review_refuted": 0,
           "rule: reviewer_rejected": 0, "rule: review_incomplete": 0,
           "rule: review_unrecorded": 0}
    for ident in published:
        out["total"] += 1
        c = classify(by_link.get((ident[0], ident[1], ident[2], int(ident[3])), []))
        kinds = c["upheld_kinds"]
        if kinds == {"verdict_pair"}:
            out["upheld: verdict_pair only"] += 1
        elif kinds == {"survivor_list"}:
            out["upheld: survivor_list only"] += 1
        elif kinds:
            out["upheld: both kinds"] += 1
        else:
            out["no upholding record"] += 1
        out["refuted on the cited article"] += c["refuted_cited"]
        out["rejected on the cited article"] += c["rejected_cited"]
        out["contrary record naming no article"] += c["contrary_without_article"]
        out["no record at all"] += not c["any"]
        out[f"rule: {rule_outcome(c)}"] += 1
    return out


INSERT_SQL = (
    f"insert into announcement_link_reviews ({', '.join(COLUMNS)})"
    f" values ({', '.join(['%s'] * len(COLUMNS))})"
)


def write_reviews(cur, rows) -> tuple[int, int]:
    """Rebuild the table from `rows` inside the caller's transaction.
    Returns (rows stored before, rows written)."""
    cur.execute("select count(*) from announcement_link_reviews")
    n_stored = cur.fetchone()[0]
    cur.execute("delete from announcement_link_reviews")
    cur.executemany(INSERT_SQL, rows)
    return n_stored, len(rows)


def _published_high_links() -> list[tuple] | str:
    """The high announcement links fct_budget_to_awards publishes, read-only;
    or the reason they could not be read."""
    try:
        import duckdb

        con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
        try:
            return con.execute(
                "select award_piid, pe_bli, exhibit, fiscal_year"
                " from fct_budget_to_awards"
                " where method = ? and confidence = 'high'", [METHOD]).fetchall()
        finally:
            con.close()
    except Exception as exc:  # reported, never silently skipped
        return f"{type(exc).__name__}: {exc}"


def pair_links(pg, pairs) -> tuple[dict, dict, dict]:
    """(links, cited, methods) for the reviewed pairs, read from Postgres:
    every budget_line_awards row of each pair, the articles its announcement
    source rows cite, and each row's method (printed, never used to filter)."""
    ordered = sorted(pairs)
    links: dict[tuple, list] = {}
    methods: dict[tuple, str] = {}
    for piid, pe, exhibit, fy, method in pg.execute(
            "select b.award_piid, b.pe_bli, b.exhibit, b.fiscal_year, b.method"
            " from budget_line_awards b"
            " join unnest(%s::text[], %s::text[]) as t(piid, pe)"
            "   on b.award_piid = t.piid and b.pe_bli = t.pe",
            ([p for p, _ in ordered], [e for _, e in ordered])).fetchall():
        links.setdefault((piid, pe), []).append((exhibit, int(fy)))
        methods[(piid, pe, exhibit, int(fy))] = method
    cited: dict[tuple, set] = {}
    for piid, pe, sid in pg.execute(
            "select award_piid, pe_bli, source_id from award_link_sources"
            " where source_kind = 'announcement'").fetchall():
        cited.setdefault((piid, pe), set()).add(sid)
    return links, cited, methods


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    verdicts, vcounts = read_verdict_files(VERDICT_DIR)
    print(f"{VERDICT_DIR.relative_to(ROOT)}: {vcounts}")
    lists, lcounts = read_result_files(ANN)
    print(f"wave{'/'.join(map(str, LIST_WAVES))}_result.json: {lcounts}")
    records = verdicts + lists

    with psycopg.connect(DSN) as pg:
        if args.dry_run:
            pg.read_only = True
        links, cited, methods = pair_links(pg, {(r.piid, r.pe_bli) for r in records})
        rows, row_counts = review_rows(records, links, cited)
        census: dict[tuple, int] = {}
        for r in rows:
            k = (r[_C["record_kind"]], r[_C["reviewer_verdict"]],
                 r[_C["adversarial_verdict"]])
            census[k] = census.get(k, 0) + 1
        by_method: dict[str, int] = {}
        for ident in {tuple(r[:4]) for r in rows}:
            m = methods[ident]
            by_method[m] = by_method.get(m, 0) + 1
        print(f"rows: {len(rows)} over {len({tuple(r[:4]) for r in rows})} link(s);"
              f" {row_counts}")
        print(f"rows by (kind, reviewer, adversarial): {dict(sorted(census.items()))}")
        print(f"reviewed links by method: {dict(sorted(by_method.items()))}")
        stored = pg.execute(
            "select award_piid, pe_bli, exhibit, fiscal_year from budget_line_awards"
            " where method = %s", (METHOD,)).fetchall()
        print(f"coverage of the {len(stored)} {METHOD} link(s) Postgres holds:"
              f" {coverage(rows, stored)}")
        published = _published_high_links()
        if isinstance(published, str):
            print(f"published-mart coverage unavailable ({published})")
        else:
            print(f"coverage of the {len(published)} high {METHOD} link(s)"
                  f" fct_budget_to_awards publishes: {coverage(rows, published)}")
        if args.dry_run:
            print("dry-run: nothing written")
            pg.rollback()
            return 0
        n_stored, n_written = write_reviews(pg.cursor(), rows)
        print(f"announcement_link_reviews: replaced {n_stored} row(s) with {n_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
