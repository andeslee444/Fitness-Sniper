<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 25a: Release-2 proof tools — the relocation report and the P1 rule list

**Spec:** §7 (proofs on pinned snapshots; "every other path must be identical, equivalent or a control-class reorder"), §8 ("Release 2 … with its own A/B on a fresh snapshot and its own rule list: narrative citation records, cite shards, program-page citation records, `pdfs/` and the link-coverage baseline"), §5.6. Task 25 is split in three: 25a (this file: tools, committed), 25b (snapshot, rehearsed writes, exports, diffs), 25c (gates, the `--revert` rehearsal, the site build and weights, the proof note). Depends on Task 24.
**Files:**
- Create: `scripts/fu/narrative_relocation_report.py`
- Create: `tests/jbooks/test_fu_narrative_relocation_report.py`
- Create: `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-r2-narratives.json`

**Interfaces:**
Consumes: `provenance_pages.book_set` (Task 23a); `scripts/fu/s195_narratives.main` (Task 23c); `tests/jbooks/narrative_volumes.py` (`seed_book_set`, `seed_pre_195_rows`, `xml_path`); `tests/jbooks/test_export_site_5f._export(pg_dsn, tmp_path)` (writes `<tmp_path>/site` and `<tmp_path>/wh.duckdb`); `export_site.fact_id_narrative`; Task 2's `govbudget.proof.load_expectations` (rule keys `path, why, status, pointer, change, required`; `*` is the only glob character and crosses `/`; 16-hex fact-ID pointer segments read `{fid}`).
Produces: `scripts/fu/narrative_relocation_report.py` — `RUN_STAMPED_KINDS`, `LOCATION_FIELDS`, `compare(a_site, b_site, *, pg_dsn, unchanged=(), watch=()) -> dict` (`{"ok", "counts": {"narrative_citations", "unchanged", "located", "relocated", "rail_pages_moved"}, "new_pdfs": {sha: bytes}, "new_pdf_bytes", "by_volume", "watched", "violations"}`; `rail_pages_moved` counts the stated-edge rail entries whose `evidence.page` differs between A's and B's program sidecars, whose rails must otherwise be equal), `main(argv=None) -> int` (CLI `--a A_SITE --b B_SITE --pg-dsn DSN [--unchanged FID]… [--watch FID]… [--report FILE]`; lines `narrative citations <n>: unchanged <u>, located <l>, relocated <r>`, `rail evidence pages moved: <m>`, `PDFs only B hosts: <k> (<bytes> bytes)`, one per watched fact ID, `  violation: …`, last line `narrative-relocation: PASS|FAIL`, exit 0/1); the P1 rule list (19 rules). Tasks 25b and 26a run them.

**Measured now** (2026-10-13): the report and the rule list were exercised on two exports of the synthetic book set, before and after `s195 --apply`, on a scratch copy of the tree with Tasks 23a–24 applied against a private Postgres 17 cluster: the tests below pass (4 then; 12 after review fix round 1 of 2026-10-15, which added the A-vs-B rail check: a dropped stated edge plus a relation/fy change on another passed `proof diff` with rule 18 matched 3, and the report did not compare A's rails with B's); `proof diff` with the rule list matched rules 0–13 and 15–17 there (2 and 17 citation-field differences, both PDFs only B hosts, `pdf_count` in both files) and left rules 14 (the receipts audit, which a bare `export_site()` call does not write) and 18 (no lineage in the synthetic book) unmet, as expected; on the real exports both match (Task 23b measured 22 evidence narratives moving; the CLI export runs the receipts step). No other file of `data/site` embeds a citation record: `grep -l hosted_pdf_url` over `data/site/json` finds only `citations.json` (and its shards) besides the receipt shards, which carry no narrative.

- [ ] **Step 1: Write the failing tests**

Create `tests/jbooks/test_fu_narrative_relocation_report.py`:

```python
"""scripts/fu/narrative_relocation_report.py — the release-2 proof's account
of what the #195 relocation changed (families piece-1 follow-ups Task 25a),
on two exports of the synthetic book set: before and after s195 --apply."""
import json

import pytest

from fu.narrative_relocation_report import compare, main  # scripts/ is on sys.path via conftest
from fu.s195_narratives import main as s195
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows, xml_path
from jbooks.test_export_site_5f import _export

from govbudget.export_site import fact_id_narrative


@pytest.fixture()
def exports(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = _export(pg_dsn, tmp_path / "a")
    assert s195(["--apply", "--pre-image", str(tmp_path / "pre.json"), "--dsn", pg_dsn]) == 0
    b = _export(pg_dsn, tmp_path / "b")
    fid = {key: fact_id_narrative(book["sha"]["BA1"], pe, "mission", xml_path(key))
           for key, pe in (("N1", "0605001TST"), ("N2", "0605002TST"), ("N4", "0605004TST"))}
    return book, a, b, fid


def _tamper(site, fid, **fields):
    path = site / "json" / "citations.json"
    cites = json.loads(path.read_text())
    cites[fid].update(fields)
    path.write_text(json.dumps(cites))


def _cites(site):
    return json.loads((site / "json" / "citations.json").read_text())


SLUG, OTHER = "0605101TST", "0605102TST"


def _edge(cites, fid, **fields):
    """A stated predecessor rail entry (export_site._emit_lineage's shape) whose
    evidence is narrative fid, on the page its citation in `cites` names."""
    return {"pe": "0605100TST", "title": "Alpha Radar (old line)", "ba": "BA 5", "fy": 2026,
            "relation": "renamed", "confidence": "stated", "resolved": True,
            "evidence": {"fact_id": fid, "page": cites[fid]["page_number"],
                         "sentence": "The Alpha program fields a new radar for the fleet."},
            **fields}


def _rail(cites, fid):
    """N1 is relocated (its page moves with the citation); N4 is kept."""
    return [_edge(cites, fid["N1"]), _edge(cites, fid["N4"], pe=OTHER)]


def _write_rail(site, *predecessors, slug=SLUG):
    path = site / "json" / "program_details" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = json.loads(path.read_text()) if path.exists() else {"pe_bli": slug}
    sidecar["lineage"] = {"rail": {"predecessors": list(predecessors), "successors": []}}
    path.write_text(json.dumps(sidecar))


def test_the_relocation_is_accounted_for(pg_dsn, exports, capsys):
    book, a, b, fid = exports
    report = compare(a, b, pg_dsn=pg_dsn, unchanged=[fid["N4"]])
    assert report["violations"] == [] and report["ok"]
    assert report["counts"] == {"narrative_citations": 6, "unchanged": 4, "located": 1, "relocated": 1,
                                "rail_pages_moved": 0}
    assert set(report["new_pdfs"]) == {book["sha"]["BA2"], book["sha"]["BA3"]}
    assert report["new_pdf_bytes"] == sum(book["path"][v].stat().st_size for v in ("BA2", "BA3"))
    assert main(["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn, "--watch", fid["N1"]]) == 0
    out = capsys.readouterr().out
    assert "narrative citations 6: unchanged 4, located 1, relocated 1" in out
    assert "rail evidence pages moved: 0" in out
    assert out.rstrip().endswith("narrative-relocation: PASS")


def test_a_rail_page_that_follows_its_citation_passes(pg_dsn, exports, capsys):
    _book, a, b, fid = exports
    _write_rail(a, *_rail(_cites(a), fid))
    _write_rail(b, *_rail(_cites(b), fid))
    report = compare(a, b, pg_dsn=pg_dsn)
    assert report["violations"] == [] and report["counts"]["rail_pages_moved"] == 1
    assert main(["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn]) == 0
    assert "rail evidence pages moved: 1" in capsys.readouterr().out


RAIL_CHANGES = {
    "an edge dropped": lambda c, fid: [_edge(c, fid["N1"])],
    "an edge added": lambda c, fid: [*_rail(c, fid), _edge(c, fid["N2"], pe="0605103TST")],
    "relation": lambda c, fid: [_edge(c, fid["N1"], relation="split"), _edge(c, fid["N4"], pe=OTHER)],
    "fy": lambda c, fid: [_edge(c, fid["N1"], fy=2027), _edge(c, fid["N4"], pe=OTHER)],
    "confidence": lambda c, fid: [_edge(c, fid["N1"], confidence="inferred"),
                                  _edge(c, fid["N4"], pe=OTHER)],
    "evidence.fact_id": lambda c, fid: [_edge(c, fid["N2"]), _edge(c, fid["N4"], pe=OTHER)],
}


@pytest.mark.parametrize("change", sorted(RAIL_CHANGES))
def test_a_rail_change_beyond_evidence_pages_fails(pg_dsn, exports, change):
    _book, a, b, fid = exports
    _write_rail(a, *_rail(_cites(a), fid))
    _write_rail(b, *RAIL_CHANGES[change](_cites(b), fid))
    assert compare(a, b, pg_dsn=pg_dsn)["violations"] == [f"rail of {SLUG} changed beyond evidence pages"]


def test_a_rail_on_one_side_only_or_off_its_citation_fails(pg_dsn, exports):
    _book, a, b, fid = exports
    ca, cb = _cites(a), _cites(b)
    _write_rail(a, *_rail(ca, fid))
    _write_rail(a, _edge(ca, fid["N4"]), slug="0605104TST")
    _write_rail(b, _edge(cb, fid["N1"]), _edge(cb, fid["N4"], pe=OTHER, evidence={
        "fact_id": fid["N4"], "page": 3, "sentence": "The Alpha program fields a new radar for the fleet."}))
    _write_rail(b, _edge(cb, fid["N4"]), slug="0605105TST")
    assert cb[fid["N4"]]["page_number"] != 3
    assert sorted(compare(a, b, pg_dsn=pg_dsn)["violations"]) == sorted([
        "rail of 0605104TST only in A", "rail of 0605105TST only in B",
        f"rail evidence {fid['N4']} on {SLUG}: page 3 is not its citation's page"])


def test_a_change_outside_the_location_fields_fails(pg_dsn, exports):
    _book, a, b, fid = exports
    _tamper(b, fid["N1"], xml_path="ProgramElement[9]/Narrative[0]")
    assert any("changed outside the location fields" in v
               for v in compare(a, b, pg_dsn=pg_dsn)["violations"])


def test_a_volume_outside_the_book_set_fails(pg_dsn, exports):
    book, a, b, fid = exports
    navy = book["sha"]["NAVY"]
    _tamper(b, fid["N1"], sha256=navy, hosted_pdf_url=f"https://cdn.example/pdfs/{navy}.pdf#page=2")
    assert any("is not in the book set of" in v for v in compare(a, b, pg_dsn=pg_dsn)["violations"])


def test_losing_a_page_or_a_pdf_fails(pg_dsn, exports):
    book, a, b, fid = exports
    _tamper(b, fid["N4"], page_number=None)
    (b / "pdfs" / f"{book['sha']['BA3']}.pdf").unlink()
    violations = compare(a, b, pg_dsn=pg_dsn, unchanged=[fid["N4"]])["violations"]
    assert f"{fid['N4']}: paged in A, pageless in B" in violations
    assert f"cited PDF {book['sha']['BA3']} is not hosted in B" in violations
    assert f"{fid['N4']} changed but must not" in violations
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_fu_narrative_relocation_report.py -q 2>&1 | tail -3`
Expected: one collection error, `ModuleNotFoundError: No module named 'fu.narrative_relocation_report'`.

- [ ] **Step 3: Write the report**

Create `scripts/fu/narrative_relocation_report.py`:

```python
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
```

- [ ] **Step 4: Write the P1 rule list**

Create `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-r2-narratives.json`:

```json
[
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/sha256", "change": ["changed"], "required": true,
   "why": "#195 (spec §5.6, Task 23b): a narrative located in another volume of its book set cites that volume's sha256; narrative_relocation_report checks each one"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/page_number", "change": ["changed"], "required": true,
   "why": "#195: located (null -> page) and relocated (page -> page) narrative citations"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/x0", "change": ["changed"], "required": true,
   "why": "#195: the first-line box of the passage on its printing page"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/x1", "change": ["changed"], "required": true,
   "why": "#195: the first-line box of the passage on its printing page"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/top_pt", "change": ["changed"], "required": true,
   "why": "#195: the first-line box of the passage on its printing page"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/bottom_pt", "change": ["changed"], "required": true,
   "why": "#195: the first-line box of the passage on its printing page"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/page_width", "change": ["changed"], "required": true,
   "why": "#195: the printing page's size (null on a pageless citation)"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/page_height", "change": ["changed"], "required": true,
   "why": "#195: the printing page's size (null on a pageless citation)"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/resolution", "change": ["changed"], "required": true,
   "why": "#195: unique / ambiguous_first on a newly located or relocated passage"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/hosted_pdf_url", "change": ["changed"], "required": true,
   "why": "#195: /pdfs/<printing volume>.pdf#page=N"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/official_url", "change": ["changed"], "required": true,
   "why": "#195: the printing volume's official URL with #page=N"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/retrieved_at", "change": ["changed"], "required": true,
   "why": "#195: the printing volume's downloaded_at (a superseded volume was downloaded at another time)"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}/*", "change": ["changed"], "required": true,
   "why": "#195: the cite shards carry the same narrative citation objects as citations.json; narrative_relocation_report checks citations.json field by field"},
  {"path": "citations/citations.parquet", "status": ["changed"], "required": true,
   "why": "#195: the same narrative citation rows' location columns"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/citation_sha256", "change": ["changed"], "required": true,
   "why": "the receipts audit fingerprints the citations.json it read, which changed"},
  {"path": "pdfs/*.pdf", "status": ["only_b"], "required": true,
   "why": "#195 (spec §5.6 point 3): every superseded volume a citation now names is hosted (20 volumes, 162,040,168 B measured 2026-10-13)"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/pdf_count", "change": ["changed"], "required": true,
   "why": "#195: the hosted PDF count grows by the superseded volumes"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/pdf_count", "change": ["changed"], "required": true,
   "why": "#195: site_meta mirrors manifest.pdf_count (not rendered: download-cards.tsx)"},
  {"path": "json/program_details/*.json", "status": ["changed"], "pointer": "/lineage/rail/*", "change": ["added", "removed"], "required": true,
   "why": "#195 (Task 23b): a stated edge's evidence page follows its narrative citation (22 of the 92 evidence narratives move); narrative_relocation_report checks every rail page"}
]
```

Deliberately no rule (any difference there FAILS P1): `data/jbook_narratives.parquet` (fact identity: the attached document), every other parquet, `json/f15_funding_history.json` (the F015E0 note receipt `e7d5bcfb4a30f458` does not move, Task 23c Step 6), `json/lineage_flow.json` (it carries fact IDs, not pages), `json/datasets.json`, `json/programs.json`, `json/search_quick.json`, every other key of a program sidecar (narratives carry no location), the receipt shards and the workbook-cell shards, every citation field outside the twelve location fields, and every citation that is not a `jbook_narrative`. Changes inside the allowed patterns are judged field by field by `narrative_relocation_report.py`.

- [ ] **Step 5: Run the tests, validate the rule list, commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_fu_narrative_relocation_report.py -q 2>&1 | tail -1
uv run --project . python -c "from govbudget.proof import load_expectations; print(len(load_expectations('docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-r2-narratives.json')), 'rules')"
uvx --offline ruff check --isolated --select F,E9 scripts/fu/narrative_relocation_report.py tests/jbooks/test_fu_narrative_relocation_report.py
```
Expected: `12 passed`; `19 rules`; `All checks passed!`. Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/scripts/fu/narrative_relocation_report.py GovBudget/tests/jbooks/test_fu_narrative_relocation_report.py GovBudget/docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-r2-narratives.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(fu): release-2 proof tools — the narrative relocation report and the P1 rule list (#195)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
