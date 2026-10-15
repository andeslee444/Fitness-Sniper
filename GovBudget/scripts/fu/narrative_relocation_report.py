#!/usr/bin/env python3
"""Release-2 proof (#195; families piece-1 follow-ups Task 25): what the
narrative relocation changed between two exports of ONE snapshot — A before
the release-2 writes, B after them — and that it changed nothing else.

  * A and B publish the same fact IDs; every citation that is not a
    jbook_narrative citation is equal field by field (retrieved_at excepted on
    the kinds each export stamps with its own run time, RUN_STAMPED_KINDS,
    as in piece 1's scripts/era/fact_stability.py);
  * a jbook_narrative citation that differs, differs only in LOCATION_FIELDS,
    and B's location is a page of a volume of its attached document's book set
    (provenance_pages.book_set; the attached sha is B's
    data/jbook_narratives.parquet document_sha256): hosted_pdf_url ends
    /<sha>.pdf#page=<p>, official_url is that volume's source_url + #page=<p>,
    retrieved_at is its downloaded_at, and B's pdfs/<sha>.pdf hashes to <sha>.
    It counts 'located' (A had no page) or 'relocated' (A had one); a paged A
    citation that B leaves pageless FAILS;
  * the PDFs only B hosts are exactly the superseded volumes B's narrative
    citations name (reported with their bytes), and B hosts every PDF A hosts;
  * data/jbook_narratives.parquet has the same rows in A and B;
  * every stated-edge rail evidence page in B's program sidecars equals the
    page of its citation in B, and every sidecar's lineage rail is the same
    in A and B with each evidence.page masked: a rail on one side only, or
    an edge added, dropped or changed in any other field, FAILS; the
    evidence pages that move are counted (rail_pages_moved);
  * --unchanged FID must be identical in A and B; --watch FID is reported.

Usage: narrative_relocation_report.py --a A_SITE --b B_SITE --pg-dsn DSN
       [--unchanged FID ...] [--watch FID ...] [--report FILE]
Last line: narrative-relocation: PASS|FAIL (exit 0|1).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

RUN_STAMPED_KINDS = frozenset({"derived", "state_file", "state_soql"})
LOCATION_FIELDS = frozenset({
    "sha256", "page_number", "x0", "x1", "top_pt", "bottom_pt", "page_width",
    "page_height", "resolution", "hosted_pdf_url", "official_url", "retrieved_at",
})


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _narrative_rows(site: Path) -> dict[str, tuple]:
    import duckdb

    pq = str(site / "data" / "jbook_narratives.parquet").replace("'", "''")
    return {r[0]: r[1:] for r in duckdb.connect().execute(
        f"select fact_id, pe_bli, project_number, kind, title, body, xml_path, org,"
        f" fiscal_year, document_sha256 from read_parquet('{pq}') where fact_id is not null"
    ).fetchall()}


def _rails(site: Path) -> dict[str, dict]:
    """slug -> the lineage rail of its program sidecar (a sidecar without one is absent)."""
    out = {}
    for path in sorted((site / "json" / "program_details").glob("*.json")):
        rail = (json.loads(path.read_text()).get("lineage") or {}).get("rail")
        if rail is not None:
            out[path.stem] = rail
    return out


def _evidence(rail: dict) -> list:
    """Each rail entry's evidence (None on an inferred edge), predecessors first."""
    return [entry.get("evidence") for side in ("predecessors", "successors")
            for entry in rail.get(side) or []]


def _page_masked(rail: dict) -> dict:
    """The rail with every evidence.page masked: all the relocation may not change."""
    masked = json.loads(json.dumps(rail))
    for evidence in _evidence(masked):
        if evidence:
            evidence["page"] = None
    return masked


def compare(a_site: Path, b_site: Path, *, pg_dsn: str, unchanged=(), watch=()) -> dict:
    import psycopg

    from govbudget.jbooks.provenance_pages import book_set

    a_site, b_site = Path(a_site), Path(b_site)
    a = json.loads((a_site / "json" / "citations.json").read_text())
    b = json.loads((b_site / "json" / "citations.json").read_text())
    narr_a, narr_b = _narrative_rows(a_site), _narrative_rows(b_site)
    violations: list[str] = []
    if set(a) != set(b):
        violations.append(f"fact IDs differ: {len(set(a) - set(b))} only in A,"
                          f" {len(set(b) - set(a))} only in B")
    if narr_a != narr_b:
        violations.append("data/jbook_narratives.parquet rows differ")
    with psycopg.connect(pg_dsn) as con:
        con.execute("set transaction read only")
        docs = {r[0]: {"id": r[1], "url": r[2], "downloaded_at": r[3], "status": r[4], "bytes": r[5]}
                for r in con.execute(
                    "select distinct on (sha256) sha256, id, source_url, downloaded_at, status, bytes"
                    " from jbook_documents where sha256 is not null order by sha256, id").fetchall()}
        sets: dict[str, set[str]] = {}

        def members(sha):
            if sha not in sets:
                sets[sha] = {v.sha256 for v in book_set(con, docs[sha]["id"])} if sha in docs else set()
            return sets[sha]

        counts = {"narrative_citations": 0, "unchanged": 0, "located": 0, "relocated": 0,
                  "rail_pages_moved": 0}
        cited_b: set[str] = set()
        by_volume: dict[str, int] = {}
        for fid in sorted(set(a) & set(b)):
            ca, cb = a[fid], b[fid]
            if ca.get("kind") != "jbook_narrative":
                bad = sorted(k for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)
                             and not (k == "retrieved_at" and ca.get("kind") in RUN_STAMPED_KINDS))
                if bad:
                    violations.append(f"{fid} ({ca.get('kind')}): {bad} changed")
                continue
            counts["narrative_citations"] += 1
            if cb.get("page_number") is not None:
                cited_b.add(cb["sha256"])
            if ca == cb:
                counts["unchanged"] += 1
                continue
            outside = sorted(k for k in set(ca) | set(cb)
                             if ca.get(k) != cb.get(k) and k not in LOCATION_FIELDS)
            if outside:
                violations.append(f"{fid}: {outside} changed outside the location fields")
                continue
            page, sha = cb.get("page_number"), cb.get("sha256")
            if page is None:
                violations.append(f"{fid}: paged in A, pageless in B")
                continue
            attached = narr_b.get(fid, (None,) * 9)[8]
            doc = docs.get(sha)
            if attached is None or sha not in members(attached):
                violations.append(f"{fid}: {sha} is not in the book set of {attached}")
                continue
            expect = {"hosted": f"/{sha}.pdf#page={page}", "official": f"{doc['url']}#page={page}",
                      "retrieved_at": doc["downloaded_at"]}
            if not (cb.get("hosted_pdf_url") or "").endswith(expect["hosted"]):
                violations.append(f"{fid}: hosted_pdf_url {cb.get('hosted_pdf_url')!r}")
            if cb.get("official_url") != expect["official"]:
                violations.append(f"{fid}: official_url {cb.get('official_url')!r}")
            stamp = cb.get("retrieved_at")
            if stamp is None or datetime.datetime.fromisoformat(stamp) != expect["retrieved_at"]:
                violations.append(f"{fid}: retrieved_at {stamp!r} is not {sha}'s downloaded_at")
            counts["located" if ca.get("page_number") is None else "relocated"] += 1
            by_volume[sha] = by_volume.get(sha, 0) + 1
        hosted_a = {p.stem for p in (a_site / "pdfs").glob("*.pdf")}
        hosted_b = {p.stem for p in (b_site / "pdfs").glob("*.pdf")}
        if hosted_a - hosted_b:
            violations.append(f"B hosts {len(hosted_a - hosted_b)} fewer PDF(s) than A")
        new_pdfs = sorted(hosted_b - hosted_a)
        expected_new = sorted(s for s in cited_b if docs.get(s, {}).get("status") == "superseded"
                              and s not in hosted_a)
        if new_pdfs != expected_new:
            violations.append(f"PDFs only B hosts {len(new_pdfs)} != superseded volumes B's"
                              f" citations name {len(expected_new)}")
        for sha in sorted(cited_b):
            path = b_site / "pdfs" / f"{sha}.pdf"
            if not path.exists():
                violations.append(f"cited PDF {sha} is not hosted in B")
            elif sha in new_pdfs and _sha_file(path) != sha:
                violations.append(f"pdfs/{sha}.pdf does not hash to its name")
    rails_a, rails_b = _rails(a_site), _rails(b_site)
    for slug in sorted(set(rails_a) ^ set(rails_b)):
        violations.append(f"rail of {slug} only in {'A' if slug in rails_a else 'B'}")
    for slug in sorted(set(rails_a) & set(rails_b)):
        if _page_masked(rails_a[slug]) != _page_masked(rails_b[slug]):
            violations.append(f"rail of {slug} changed beyond evidence pages")
            continue
        counts["rail_pages_moved"] += sum(
            (ev_a or {}).get("page") != (ev_b or {}).get("page")
            for ev_a, ev_b in zip(_evidence(rails_a[slug]), _evidence(rails_b[slug])))
    for slug, rail in sorted(rails_b.items()):
        for ev in _evidence(rail):
            if ev and ev.get("page") != b.get(ev["fact_id"], {}).get("page_number"):
                violations.append(f"rail evidence {ev['fact_id']} on {slug}: page {ev.get('page')}"
                                  " is not its citation's page")
    for fid in unchanged:
        if a.get(fid) != b.get(fid):
            violations.append(f"{fid} changed but must not")
    watched = {fid: {"a": {k: a.get(fid, {}).get(k) for k in ("sha256", "page_number")},
                     "b": {k: b.get(fid, {}).get(k) for k in ("sha256", "page_number")}}
               for fid in (*unchanged, *watch)}
    return {"ok": not violations, "counts": counts,
            "new_pdfs": {s: docs[s]["bytes"] for s in new_pdfs},
            "new_pdf_bytes": sum(docs[s]["bytes"] or 0 for s in new_pdfs),
            "by_volume": dict(sorted(by_volume.items())), "watched": watched,
            "violations": violations}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--pg-dsn", required=True, dest="pg_dsn")
    ap.add_argument("--unchanged", action="append", default=[])
    ap.add_argument("--watch", action="append", default=[])
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args(argv)
    report = compare(args.a, args.b, pg_dsn=args.pg_dsn, unchanged=args.unchanged,
                     watch=args.watch)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    c = report["counts"]
    print(f"narrative citations {c['narrative_citations']}: unchanged {c['unchanged']},"
          f" located {c['located']}, relocated {c['relocated']}")
    print(f"rail evidence pages moved: {c['rail_pages_moved']}")
    print(f"PDFs only B hosts: {len(report['new_pdfs'])} ({report['new_pdf_bytes']:,} bytes)")
    for fid, w in report["watched"].items():
        print(f"  {fid}: A {w['a']} -> B {w['b']}")
    for v in report["violations"][:40]:
        print(f"  violation: {v}")
    print(f"narrative-relocation: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
