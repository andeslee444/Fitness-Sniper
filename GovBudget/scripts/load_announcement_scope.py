"""Record what the announcement LLM-alias pass covered (ROADMAP findings :118-119).

Reads the two derived artifacts the wave-4 machinery writes and upserts ONE row
into announcement_llm_scope, which export_site._announcement_llm_scope turns
into site_meta.announcement_llm_scope and /methodology/ states in prose. No
figure on that page about this pass is typed by hand any more.

  residue_manifest.json : records_total / records_with_lake_piid /
                          records_deterministic / records_residue /
                          value_residue / earlier_pass{name,records,value} /
                          chunks[{file, org, records, announced_value}]
  wave4_result.json     : chunks_attempted[] — which chunks actually came back

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
tier pinned to its own draw).

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


def scope_row(manifest: dict, result: dict, as_of: str,
              precision_sample_id: str | None = None) -> tuple:
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
    return (
        as_of,
        manifest["records_with_lake_piid"],
        manifest["records_deterministic"],
        manifest["records_residue"],
        earlier["records"] + wave4_records,
        manifest["value_residue"],
        earlier["value"] + wave4_value,
        f"{earlier['name']} + wave4 ({len(attempted_files)} of "
        f"{len(manifest['chunks'])} chunks adjudicated)",
        precision_sample_id,
    )


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
    row = scope_row(manifest, result, args.as_of, args.precision_sample_id)
    print("announcement_llm_scope row:", row)
    if args.precision_sample_id:
        with psycopg.connect(DSN) as pg:
            n = check_precision_sample(pg, args.precision_sample_id, result)
        print(f"precision sample {args.precision_sample_id}: {n} verdict(s),"
              f" every judged pair is one of this wave's {len(result['surviving'])}"
              " survivors")
    if args.dry_run:
        return 0
    with psycopg.connect(DSN) as pg:
        pg.execute(
            "insert into announcement_llm_scope (as_of, records_total,"
            " records_deterministic, records_residue, records_attempted,"
            " value_residue, value_attempted, note, precision_sample_id)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (as_of) do update set"
            "   records_total=excluded.records_total,"
            "   records_deterministic=excluded.records_deterministic,"
            "   records_residue=excluded.records_residue,"
            "   records_attempted=excluded.records_attempted,"
            "   value_residue=excluded.value_residue,"
            "   value_attempted=excluded.value_attempted,"
            "   note=excluded.note,"
            "   precision_sample_id=excluded.precision_sample_id", row)
        pg.commit()
        print("rows:", pg.execute(
            "select as_of, records_attempted, records_residue, precision_sample_id"
            " from announcement_llm_scope order by as_of").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
