"""Record what the announcement LLM-alias pass covered (ROADMAP findings :118-119).

Reads the two derived artifacts the wave-4 machinery writes and upserts ONE row
into announcement_llm_scope, which export_site._announcement_llm_scope turns
into site_meta.announcement_llm_scope and /methodology/ states in prose. No
figure on that page about this pass is typed by hand any more.

  residue_manifest.json : records_total / records_with_lake_piid /
                          records_deterministic / records_residue /
                          value_residue /
                          earlier_pass{name,records,value,
                                       records_in_residue,value_in_residue} /
                          chunks[{file, org, records, announced_value}]
  wave4_result.json     : chunks_attempted[] — which chunks actually came back
  wave{1,2,3}_result.json : surviving[] — which pairs PREDATE this pass

Only the earlier pass's IN-RESIDUE subset is added to wave 4's count: its own
`records`/`value` are an entry count over a population taken before the
lexicon grew, and are not a subset of today's residue (fix round 1, item 1).

"attempted" is what was ADJUDICATED, never what was queued: a pass stopped
halfway must publish the smaller true number.

records_total is the manifest's records_with_lake_piid, not its records_total:
the residue is defined over records that join the award lake, and
records_deterministic + records_residue must partition exactly that set
(migration 016's residue_partitions_total constraint enforces it).

--precision-sample-id names the held-out study run that measured THIS pass's
own links (link_precision_samples.sample_id). It is checked here, at write
time, against the wave's surviving pairs: a run holding a pair the wave did not
produce is refused, so the exporter's read-side query only has to name the run.
The tier-wide study is a different measurement over a different population and
is never used for this figure (export_site._PINNED_PRECISION_SAMPLES keeps the
tier pinned to its own draw). `links_new_this_pass` counts how far apart those
populations are: links the corpus publishes under `announcement+lexicon` that
only this pass produced, and that the 2026-09-04 tier draw therefore could not
have sampled. /methodology/ states it where it states the tier figure.

ONE ROW PER as_of, and a re-run on the same date REPLACES that day's row
(`on conflict (as_of) do update`). Rows from earlier dates are kept, and are
the record of what the page said before. Migration 016's own comment says
rows are "never updated in place"; that is wrong, and 017's comment carries
the correction — an applied migration file is never edited.

Usage: uv run python scripts/load_announcement_scope.py [--dry-run] [--as-of YYYY-MM-DD]
                                                        [--precision-sample-id ID]
"""
import argparse
import json
from datetime import date
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "research" / "announcements"
DSN = "postgresql://localhost/govbudget"

#: The wave result files that PRECEDE this pass, in the order the link loader
#: is given them. Their surviving pairs are what makes a wave-4 pair "new":
#: a pair an earlier wave produced was already in the announcement tier when
#: the tier-wide precision sample was drawn.
EARLIER_WAVES = ("wave1_result.json", "wave2_result.json", "wave3_result.json")


def scope_row(manifest: dict, result: dict, as_of: str,
              precision_sample_id: str | None = None,
              links_new_this_pass: int | None = None) -> tuple:
    attempted_files = set(result.get("chunks_attempted", []))
    by_file = {c["file"]: c for c in manifest["chunks"]}
    missing = sorted(attempted_files - set(by_file))
    if missing:
        raise SystemExit(
            f"wave4_result.json names chunks the manifest does not: {missing[:5]}"
            " — re-run `mine_announcement_residue.py queue` and `collect` in that order")
    wave4_records = sum(by_file[f]["records"] for f in attempted_files)
    wave4_value = sum(by_file[f]["announced_value"] for f in attempted_files)
    if wave4_records != result["records_attempted"]:
        raise SystemExit(
            f"manifest says {wave4_records} records in the adjudicated chunks, "
            f"wave4_result.json says {result['records_attempted']}")
    earlier = manifest["earlier_pass"]
    # THE EARLIER PASS'S IN-RESIDUE SUBSET, never its own totals (fix round 1,
    # item 1). `earlier["records"]`/`["value"]` are what the wave-2 pass was
    # HANDED: an entry count over 3,840 rows with 8 duplicate keys, taken
    # before the lexicon learned names that now match some of those records
    # deterministically — i.e. before they left the residue. Added to wave 4's
    # count it made /methodology/ publish 15,615 records and 89.4% of the
    # residue by value where the true in-residue figures were smaller, and the
    # unattempted tail correspondingly larger. `mine_announcement_residue.
    # earlier_pass_in_residue` intersects the pass with TODAY's residue and the
    # manifest publishes the result; a manifest that predates it is refused
    # rather than read the old way.
    for field in ("records_in_residue", "value_in_residue"):
        if field not in earlier:
            raise SystemExit(
                f"residue_manifest.json earlier_pass has no {field!r} — it was"
                " written before the earlier pass was intersected with the"
                " residue, and its entry count is not a subset of"
                " records_residue; re-run"
                " `uv run python scripts/mine_announcement_residue.py queue`")
    return (
        as_of,
        manifest["records_with_lake_piid"],
        manifest["records_deterministic"],
        manifest["records_residue"],
        earlier["records_in_residue"] + wave4_records,
        manifest["value_residue"],
        earlier["value_in_residue"] + wave4_value,
        f"{earlier['name']} + wave4 ({len(attempted_files)} of "
        f"{len(manifest['chunks'])} chunks adjudicated)",
        precision_sample_id,
        links_new_this_pass,
    )


def _pairs(result: dict) -> set[tuple[str, str]]:
    """The (piid, pe_bli) pairs a wave result file says survived both lenses.
    `pe_bli` is stripped, like the packets and the link loader strip it."""
    return {(s["piid"], str(s["pe_bli"]).strip())
            for s in result.get("surviving", [])}


def new_links_published(pg, result: dict, earlier_results: list[dict]) -> int:
    """Links the corpus publishes under `announcement+lexicon` that ONLY this
    pass produced — the frame the tier-wide precision draw could not cover.

    /methodology/ publishes the announcement tier's precision from the
    2026-09-04 stratified draw (pinned by export_site.
    _PINNED_PRECISION_SAMPLES). That draw was made over the tier as it then
    stood; a pass that adds links to the tier afterwards makes the figure
    describe a population the reader cannot see the edge of. This count is the
    edge, and the page states it beside the tier figure.

    Both halves are needed. A pair an EARLIER wave also produced was already
    in the tier when the draw was made, so it is not new; a pair the corpus
    does not publish under this method today is not in the tier at all.
    """
    mine = _pairs(result) - {p for r in earlier_results for p in _pairs(r)}
    if not mine:
        return 0
    ordered = sorted(mine)
    row = pg.execute(
        "select count(*) from ("
        "  select distinct b.award_piid, b.pe_bli"
        "  from budget_line_awards b"
        "  join unnest(%(piids)s::text[], %(pes)s::text[]) as t(piid, pe)"
        "    on b.award_piid = t.piid and b.pe_bli = t.pe"
        "  where b.method = 'announcement+lexicon'"
        "    and b.confidence in ('high', 'medium')) q",
        {"piids": [p for p, _ in ordered], "pes": [b for _, b in ordered]},
    ).fetchone()
    return int(row[0])


def check_precision_sample(pg, sample_id: str, result: dict) -> int:
    """Refuse a sample that is not a sample of THIS pass's survivors.

    The page says the pair measures the links this pass produced. Nothing on
    the read side can tell one sample_id from another, so the claim is made
    true here: every judged pair in the run must appear in the wave's own
    `surviving` list. Returns how many verdicts the run holds.
    """
    survivors = {(s["piid"], str(s["pe_bli"]).strip()) for s in result["surviving"]}
    rows = pg.execute(
        "select award_piid, pe_bli, rubric from link_precision_samples"
        " where sample_id = %s", (sample_id,)).fetchall()
    if not rows:
        raise SystemExit(
            f"link_precision_samples holds no verdict under sample_id {sample_id!r}"
            " — run scripts/precision_study.py load first, or omit"
            " --precision-sample-id until the sample is judged")
    wrong_rubric = sorted({r[2] for r in rows if r[2] != "attribution"})
    if wrong_rubric:
        raise SystemExit(
            f"sample {sample_id!r} holds verdicts under rubric(s) {wrong_rubric} —"
            " only 'attribution' is published as precision (migration 015)")
    stray = sorted({(p, b) for p, b, _ in rows} - survivors)
    if stray:
        raise SystemExit(
            f"sample {sample_id!r} judges {len(stray)} pair(s) this wave did not"
            f" produce, e.g. {stray[:3]} — the page would call it a measurement of"
            " this pass's links; draw the sample from the wave packets")
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--precision-sample-id",
                    help="link_precision_samples.sample_id of the held-out"
                         " sample drawn from this wave's surviving links")
    args = ap.parse_args()

    manifest = json.loads((ANN / "residue_manifest.json").read_text())
    result = json.loads((ANN / "wave4_result.json").read_text())
    earlier_results = [json.loads((ANN / f).read_text()) for f in EARLIER_WAVES]
    earlier_pairs = {p for r in earlier_results for p in _pairs(r)}
    with psycopg.connect(DSN) as pg:
        new_links = new_links_published(pg, result, earlier_results)
    row = scope_row(manifest, result, args.as_of, args.precision_sample_id,
                    links_new_this_pass=new_links)
    print("announcement_llm_scope row:", row)
    print(f"links only this pass publishes under announcement+lexicon:"
          f" {new_links} (of {len(_pairs(result) - earlier_pairs)} surviving pairs"
          f" no earlier wave produced) — the 2026-09-04 tier draw predates them")
    if args.precision_sample_id:
        with psycopg.connect(DSN) as pg:
            n = check_precision_sample(pg, args.precision_sample_id, result)
            judged = {(p, b) for p, b in pg.execute(
                "select award_piid, pe_bli from link_precision_samples"
                " where sample_id = %s", (args.precision_sample_id,)).fetchall()}
        # DISCLOSED, not corrected (fix round 1, item 11): the draw is over the
        # wave's survivors, and a survivor an earlier wave also produced is a
        # link that predates this round. The sample stays as drawn — re-drawing
        # it after the fact is the worse failure — so the overlap is stated
        # here and in the report instead.
        predating = len(judged & earlier_pairs)
        print(f"precision sample {args.precision_sample_id}: {n} verdict(s),"
              f" every judged pair is one of this wave's {len(result['surviving'])}"
              f" survivors; {predating} of them also survive in an earlier wave"
              " and so predate this round")
    if args.dry_run:
        return 0
    with psycopg.connect(DSN) as pg:
        pg.execute(
            "insert into announcement_llm_scope (as_of, records_total,"
            " records_deterministic, records_residue, records_attempted,"
            " value_residue, value_attempted, note, precision_sample_id,"
            " links_new_this_pass)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (as_of) do update set"
            "   records_total=excluded.records_total,"
            "   records_deterministic=excluded.records_deterministic,"
            "   records_residue=excluded.records_residue,"
            "   records_attempted=excluded.records_attempted,"
            "   value_residue=excluded.value_residue,"
            "   value_attempted=excluded.value_attempted,"
            "   note=excluded.note,"
            "   precision_sample_id=excluded.precision_sample_id,"
            "   links_new_this_pass=excluded.links_new_this_pass", row)
        pg.commit()
        print("rows:", pg.execute(
            "select as_of, records_attempted, records_residue, precision_sample_id"
            " from announcement_llm_scope order by as_of").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
