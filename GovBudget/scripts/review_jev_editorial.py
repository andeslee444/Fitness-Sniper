"""Prepare/run one bounded Jev dossier review. Run with uv run python scripts/review_jev_editorial.py.

Default prepares evidence without making API calls; --run executes one frozen batch.
Use a new --out directory per run. Existing results are never silently overwritten.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path

from govbudget.dossiers.editorial_review import prepare_batch, digest, RUBRIC_VERSION
from probe_jev import ROOT, MODEL, ENDPOINT, evaluate, load_key


def prepared_batch(out: Path, *, root: Path, run: bool) -> list[dict]:
    """Reuse a frozen packet on --run; never replace previously prepared evidence."""
    if (out / "results.jsonl").exists():
        raise ValueError("Existing results retained; choose a new output directory.")
    cases_file, manifest_file = out / "cases.json", out / "manifest.json"
    if cases_file.exists() or manifest_file.exists():
        if not run:
            raise ValueError("Existing preparation retained; use --run or a new output directory.")
        if not cases_file.exists() or not manifest_file.exists():
            raise ValueError("Incomplete preparation retained; choose a new output directory.")
        cases = json.loads(cases_file.read_text())
        manifest = json.loads(manifest_file.read_text())
        if manifest.get("cases_sha256") != digest(cases):
            raise ValueError("Prepared cases changed; choose a new output directory.")
        if manifest.get("model") != MODEL or manifest.get("endpoint") != ENDPOINT:
            raise ValueError("Prepared provider changed; choose a new output directory.")
        return cases
    cases = prepare_batch(root)
    out.mkdir(parents=True, exist_ok=True)
    cases_file.write_text(json.dumps(cases, indent=2) + "\n")
    manifest = {"prepared_at": datetime.now(timezone.utc).isoformat(), "model": MODEL,
        "endpoint": ENDPOINT, "rubric_version": RUBRIC_VERSION, "cases_sha256": digest(cases),
        "case_count": len(cases), "label_status": "Unlabeled real-content review; not a human holdout.",
        "publication_authority": False, "human_review_seconds": None}
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "data/research/jev-editorial/2026-09-22")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    try:
        cases = prepared_batch(args.out, root=ROOT, run=args.run)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if not args.run:
        print(f"Prepared {len(cases)} claims; no API requests made.")
        return
    key = load_key()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda case: evaluate(case, key), cases))
    for result in results:
        # No labels exist yet. Do not score null labels as model errors.
        result.pop("correct", None)
        result.pop("expected", None)
        choice = result.get("answers", {}).get("verdict", {}).get("choice")
        result["review_required"] = True  # Even a model-supported claim needs review.
        result["model_flag"] = choice != "supported"
    (args.out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
    good = [r for r in results if r["status"] == "ok"]
    summary = {"claims": len(cases), "completed": len(good), "errors": len(results)-len(good),
        "structural_citation_passes": sum(c["checks"]["citation_resolves"] for c in cases),
        "deterministic_flagged_claims": sum(bool(c["checks"]["flags"]) for c in cases),
        "model_flagged_claims": sum(r["model_flag"] for r in good),
        "model_supported_claims": sum(not r["model_flag"] for r in good),
        "not_established_claims": sum(r["answers"]["verdict"]["choice"] == "not_established" for r in good),
        "false_approvals": None, "false_flags": None, "net_human_reviewer_seconds": None,
        "decision": "Keep offline; human labels and reviewer-time comparison required before expansion."}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    # A side-by-side markdown queue is the actual editorial deliverable.
    queue = ["# Jev editorial review queue", "", "Internal only. Model decisions are review flags, never publication approval.", "",
             "Human labels and reviewer time are unmeasured. Full source records and hashes are in cases.json.", ""]
    for case, result in zip(cases, results, strict=True):
        verdict = result.get("answers", {}).get("verdict", {}).get("choice", "error")
        queue += [f"## {case['id']}", "", case["state"]["claim"], "", f"Model: **{verdict}**. Local flags: {', '.join(case['checks']['flags']) or 'none'}.", "",
                  "Exact cited evidence:", "", "```json", json.dumps(case["state"]["evidence"], indent=2), "```", "",
                  "Human verdict: pending. Useful correction: pending. Review time: unmeasured.", ""]
    (args.out / "review-queue.md").write_text("\n".join(queue))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
