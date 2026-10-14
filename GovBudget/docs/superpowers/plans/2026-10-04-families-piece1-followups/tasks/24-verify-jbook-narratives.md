<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 24: ★ #195 — `verify-jbook-narratives`, the printed-in check (verify-phase5b1 gate 5)

**Spec:** §5.6 (Design A, point 4: the full-population check, its paged rule, the pageless rule, the honest unresolved count), §2.3 Q26 (`OPENING_ONLY_CEILING = 111`, a ratchet), §6 (the CLI convention: a check that fails exits 1, a tool error prints `<tool>: ERROR — <message>` and exits 2), §7 W5. Depends on Task 23c (its tests write the relocation through `scripts/fu/s195_narratives.py`).
**Files:**
- Create: `src/govbudget/verify_jbook_narratives.py`
- Create: `tests/jbooks/test_verify_jbook_narratives.py`
- Modify: `src/govbudget/cli.py` — gate 5 inserted directly above `    # Gate 3: coverage (non-gating)` (line 2105 today, in `cmd_verify_phase5b1`); `cmd_verify_jbook_narratives` inserted directly above `def cmd_verify_phase5e(args) -> None:`; the subcommand registered directly after the two `v5b1` lines (3314–3315 today)
- Modify: `src/govbudget/verify_phase5b1.py` — the module docstring's gate list (anchor on `                          (the pre-5F state).`)
- Modify: `docs/superpowers/LAUNCH.md` — Step 3 (anchor on ``Expected: `verify-phase5b1: PASS` ``, line 327 today)

Line numbers are hints; anchor on the quoted text.

**Interfaces:**
Consumes: Task 23a's `provenance_pages.{book_set, fact_anchor, narrative_opening, narrative_closing, narrative_printed_at, narrative_located_at, normalize_ws, page_texts_parallel}` (BINDING: the check and the relocation decide "printed" and "located" with the same functions); Task 23b's export (a located citation names its printing volume and that volume is in `pdfs/`); Task 23c's `scripts/fu/s195_narratives.py` `main(argv) -> int`; `tests/jbooks/narrative_volumes.py`; `tests/jbooks/test_export_site_5f._export`; `cli.main(argv=None)`; `config.SITE_DIR`, `config.PG_DSN`.
Produces: `govbudget.verify_jbook_narratives` — `OPENING_ONLY_CEILING = 111`, `PAGELESS_OPENING_SEEN_CEILING = 77`, `verify_jbook_narratives(site_dir, *, pg_dsn, opening_only_ceiling=111, opening_seen_ceiling=77, texts_for=None) -> dict` (`{"ok", "counts": {"citations", "paged", "printed", "opening_only", "pageless", "opening_seen", "opening_nowhere"}, "opening_only": [fid], "opening_seen": [fid], "ceilings": {"opening_only", "opening_seen"}, "failures": [(fid or "*", reason)]}`; raises `FileNotFoundError` / `LookupError` on a missing input), `format_report(report) -> list[str]`; CLI `govbudget verify-jbook-narratives [--site-dir DIR] [--pg-dsn DSN]` (last line `verify-jbook-narratives: PASS|FAIL`, exit 0/1; `verify-jbook-narratives: ERROR — …` and exit 2 on a missing input); `verify-phase5b1` prints `gate 5 narrative printed-in: → PASS|FAIL` and the report lines indented, and fails when gate 5 fails (so `verify-phase5`'s assembly, which runs `verify-phase5b1`, carries it). Tasks 25 and 26 run it.

**Measured now** (2026-10-13, read-only, a prototype of this module run on the 916ae88e export in `data/site` and live Postgres, with the page texts of `work/g6/textcache/`): 11,717 narrative citations; paged 6,096 — 5,757 printed where cited, 339 `opening_only`, 0 whose page lacks the opening; pageless 5,621 — 4,177 located in their book set (so they FAIL today: 4,157 PB2026 plus the 20 lineage-evidence citations of PB2017–PB2025 of contract issue G6-3), 77 whose opening a volume prints without the closing (`opening_seen`), 1,367 whose opening no volume prints. After Task 23c's relocation on the same state (Task 23a's plan, with the 19 missing lineage-evidence rows built): printed 5,757 + 4,158 + 228 + 19 = 10,162, `opening_only` 111, pageless 1,444 (77 + 1,367), 0 failures. The two ceilings are those measured counts: 111 is Q26's; 77 is new (contract issue G6-2: design §5.6 counted those 77 as printed and expected "about 1,370" unresolved; an opening alone is the evidence that put `033016199ca94aa7` on the wrong exhibit, so they stay pageless and are ratcheted the same way — a ratchet the owner has not approved, so Step 0 asks before anything here is written; README Product rules: a ratchet holds only an owner-approved count). A pypdf text pass over the 103 PDFs of those book sets took 1,026 s single-threaded on this machine; `page_texts_parallel` spreads it over up to 8 processes.

- [ ] **Step 0: ★ Owner approval of the second ratchet, 77 (before any file of this task is written)**

Spec §5.6's owner-approved pageless rule is "a pageless citation's opening must appear in no volume of its group"; Q26 approved a ratchet for the 111 `opening_only` citations only. Tell the owner: "Gate 5 per spec §5.6 fails 77 pageless citations whose opening a volume prints without the closing words within three pages (design §5.6 had counted them as printed; an opening alone is the evidence that put `033016199ca94aa7` on the wrong exhibit). I propose keeping them pageless and ratcheting them at `PAGELESS_OPENING_SEEN_CEILING = 77`, as Q26 does for the 111: the gate fails if the count ever rises, and the ceiling is lowered, never raised, when it falls. Approve?" Wait for an explicit yes, and record the answer and its date in this task's commit message (Step 6) and the release-2 stamp (Task 26b Step 5).

On a no, do not land this task as drafted: the literal §5.6 rule (`PAGELESS_OPENING_SEEN_CEILING = 0`) fails these 77 on every run, so release 2 cannot pass gate 5 until each has a page. Ask the owner which rule places them (for example: cite the page that prints the opening and count them under the `opening_only` ratchet, 111 + 77 = 188, which also needs the owner), and amend Tasks 23a, 24, 25a–25c and 26b to that answer before going on.

- [ ] **Step 1: Write the failing tests**

Create `tests/jbooks/test_verify_jbook_narratives.py`:

```python
"""verify-jbook-narratives (#195; families piece-1 follow-ups Task 24): every
jbook_narrative citation names a document that prints the passage. Exports the
synthetic book set (tests/jbooks/narrative_volumes.py) before and after the
#195 relocation and checks the export."""
import duckdb
import psycopg
import pytest

from fu.s195_narratives import main as s195  # scripts/ is on sys.path via conftest
from govbudget import cli
from govbudget.verify_jbook_narratives import (
    OPENING_ONLY_CEILING,
    PAGELESS_OPENING_SEEN_CEILING,
    format_report,
    verify_jbook_narratives,
)
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows
from jbooks.test_export_site_5f import _export


def _site(pg_dsn, tmp_path, *, relocate):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    if relocate:
        assert s195(["--apply", "--pre-image", str(tmp_path / "pre.json"), "--dsn", pg_dsn]) == 0
    return book, _export(pg_dsn, tmp_path)


def _check(site, pg_dsn, **ceilings):
    return verify_jbook_narratives(site, pg_dsn=pg_dsn, **{
        "opening_only_ceiling": 1, "opening_seen_ceiling": 0, **ceilings})


def _fid_of(site, pe_bli):
    narr = site / "data" / "jbook_narratives.parquet"
    return duckdb.sql(f"select fact_id from read_parquet('{narr}') where pe_bli = '{pe_bli}'").fetchone()[0]


def test_the_ceilings_are_the_measured_counts():
    assert (OPENING_ONLY_CEILING, PAGELESS_OPENING_SEEN_CEILING) == (111, 77)


def test_the_pre_195_export_fails(pg_dsn, tmp_path):
    book, site = _site(pg_dsn, tmp_path, relocate=False)
    report = _check(site, pg_dsn)
    assert not report["ok"]
    assert report["counts"] == {"citations": 6, "paged": 3, "printed": 1, "opening_only": 2,
                                "pageless": 3, "opening_seen": 0, "opening_nowhere": 2}
    reasons = dict(report["failures"])
    assert reasons[_fid_of(site, "0605002TST")] == (
        f"pageless, but located at {book['sha']['BA3']} page 1")
    assert reasons["*"] == "2 opening-only paged citations, above the ceiling of 1"


def test_the_relocated_export_passes(pg_dsn, tmp_path):
    _book, site = _site(pg_dsn, tmp_path, relocate=True)
    report = _check(site, pg_dsn)
    assert report["failures"] == [] and report["ok"]
    assert report["counts"] == {"citations": 6, "paged": 4, "printed": 3, "opening_only": 1,
                                "pageless": 2, "opening_seen": 0, "opening_nowhere": 2}
    assert report["opening_only"] == [_fid_of(site, "0605005TST")]
    assert format_report(report)[0] == (
        "narrative citations 6: paged 4 (printed 3, opening_only 1 of at most 1);"
        " pageless 2 (opening printed without its closing 0 of at most 0, opening"
        " printed nowhere 2)")


def test_the_opening_only_count_is_a_ratchet(pg_dsn, tmp_path):
    _book, site = _site(pg_dsn, tmp_path, relocate=True)
    report = _check(site, pg_dsn, opening_only_ceiling=0)
    assert report["failures"] == [("*", "1 opening-only paged citations, above the ceiling of 0")]


def test_a_pageless_opening_without_its_closing_is_counted_and_ratcheted(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update provenance_pages set page_number = null, x0 = null, x1 = null,"
                    " top_pt = null, bottom_pt = null, page_width = null, page_height = null,"
                    " resolution = 'unresolved' where pe_bli = '0605005TST'")
    assert s195(["--apply", "--pre-image", str(tmp_path / "pre.json"), "--dsn", pg_dsn]) == 0
    site = _export(pg_dsn, tmp_path)
    report = _check(site, pg_dsn, opening_seen_ceiling=1)
    assert report["ok"] and report["opening_seen"] == [_fid_of(site, "0605005TST")]
    assert _check(site, pg_dsn)["failures"] == [
        ("*", "1 pageless citations with their opening printed, above the ceiling of 0")]


def test_a_page_that_does_not_print_the_opening_fails(pg_dsn, tmp_path):
    _book, site = _site(pg_dsn, tmp_path, relocate=True)
    fid = _fid_of(site, "0605004TST")
    pq = site / "citations" / "citations.parquet"
    con = duckdb.connect()
    con.execute(f"create table c as select * from read_parquet('{pq}')")
    con.execute("update c set page_number = 1,"
                " hosted_pdf_url = replace(hosted_pdf_url, '#page=2', '#page=1'),"
                " official_url = replace(official_url, '#page=2', '#page=1')"
                " where fact_id = ?", [fid])
    con.execute(f"copy c to '{pq}' (format parquet)")
    con.close()
    reasons = dict(_check(site, pg_dsn)["failures"])
    assert reasons[fid].startswith("opening not printed on page 1")


def test_an_unhosted_or_altered_volume_fails(pg_dsn, tmp_path):
    book, site = _site(pg_dsn, tmp_path, relocate=True)
    (site / "pdfs" / f"{book['sha']['BA2']}.pdf").unlink()
    (site / "pdfs" / f"{book['sha']['BA3']}.pdf").write_bytes(b"%PDF-1.4 altered")
    reasons = dict(_check(site, pg_dsn)["failures"])
    assert reasons[_fid_of(site, "0605001TST")] == f"cited PDF {book['sha']['BA2']} is not hosted in pdfs/"
    assert reasons[_fid_of(site, "0605002TST")].startswith("sha256 mismatch:")


def test_a_missing_input_is_a_tool_error(pg_dsn, tmp_path):
    with pytest.raises(FileNotFoundError):
        verify_jbook_narratives(tmp_path / "nowhere", pg_dsn=pg_dsn)


def test_cli_exit_codes(pg_dsn, tmp_path, capsys):
    _book, site = _site(pg_dsn, tmp_path, relocate=False)
    argv = ["verify-jbook-narratives", "--site-dir", str(site), "--pg-dsn", pg_dsn]
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    out = capsys.readouterr().out.splitlines()
    assert exc.value.code == 1 and out[-1] == "verify-jbook-narratives: FAIL"
    with pytest.raises(SystemExit) as exc:
        cli.main(["verify-jbook-narratives", "--site-dir", str(tmp_path / "x"), "--pg-dsn", pg_dsn])
    assert exc.value.code == 2
    assert capsys.readouterr().out.startswith("verify-jbook-narratives: ERROR — ")


def test_verify_phase5b1_runs_it_as_gate_5(monkeypatch, capsys):
    import govbudget.verify_jbook_narratives as vjn
    import govbudget.verify_phase5b1 as v

    monkeypatch.setattr(v, "citation_gate5b1", lambda site: {
        "ok": True, "sampled": 1, "passed": 1, "failures": [], "row_label": {}})
    monkeypatch.setattr(v, "integrity_gate5b1", lambda site: {"ok": True, "checks": {}, "failures": []})
    monkeypatch.setattr(v, "narrative_gate5b1", lambda site: {
        "ok": True, "narrative_total": 1, "resolved_total": 1, "sampled": 1, "passed": 1,
        "failures": []})
    monkeypatch.setattr(v, "coverage_report5b1", lambda site: {})
    report = {"ok": False, "counts": {"citations": 1, "paged": 1, "printed": 0,
                                      "opening_only": 0, "pageless": 0, "opening_seen": 0,
                                      "opening_nowhere": 0},
              "ceilings": {"opening_only": 111, "opening_seen": 77},
              "failures": [("f1", "opening not printed on page 3: 'x'")]}
    monkeypatch.setattr(vjn, "verify_jbook_narratives", lambda site, **kw: report)
    with pytest.raises(SystemExit) as exc:
        cli.main(["verify-phase5b1"])
    out = capsys.readouterr().out
    assert exc.value.code == 1
    assert "gate 5 narrative printed-in: → FAIL" in out
    assert "  FAIL f1: opening not printed on page 3: 'x'" in out
    report["ok"], report["failures"] = True, []
    with pytest.raises(SystemExit) as exc:
        cli.main(["verify-phase5b1"])
    assert exc.value.code == 0 and "gate 5 narrative printed-in: → PASS" in capsys.readouterr().out
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_verify_jbook_narratives.py -q 2>&1 | tail -3`
Expected: one collection error, `ModuleNotFoundError: No module named 'govbudget.verify_jbook_narratives'`.

- [ ] **Step 3: Write the check**

Create `src/govbudget/verify_jbook_narratives.py`:

```python
"""verify-jbook-narratives: every jbook_narrative citation names a document
that prints the passage (#195; families piece-1 follow-ups design §5.6 point 4,
Q26; Task 24). Gate 5 of verify-phase5b1, and its own CLI.

Full population: every jbook_narrative citation in <site>/citations/
citations.parquet, joined to <site>/data/jbook_narratives.parquet for its body,
its PE/BLI and the document it is attached to. Its own text pass: pypdf page
texts of every volume of every attached document's book set
(provenance_pages.book_set, read from Postgres), from the hosted copy
<site>/pdfs/<sha>.pdf when there is one, else from jbook_documents.file_path,
the bytes checked against the sha either way.

  paged     the cited volume is in the attached document's book set and hosted
            (<site>/pdfs/<sha>.pdf), hosted_pdf_url ends /<sha>.pdf#page=<p>
            and official_url ends #page=<p>, and page p prints the opening
            (narrative_opening). 'printed' when the closing (narrative_closing)
            follows within NARRATIVE_CLOSING_SPAN_PAGES pages
            (narrative_printed_at); otherwise 'opening_only', counted, and FAIL
            above OPENING_ONLY_CEILING. An opening not on the page is a FAIL.
  pageless  the citation names its attached document, and no page of any
            volume of the book set locates it (narrative_located_at: opening,
            closing within three pages, PE anchor on the page): a page that
            does is a location the relocation missed, FAIL. A pageless
            citation whose opening a volume prints without that is
            'opening_seen', counted, and FAIL above
            PAGELESS_OPENING_SEEN_CEILING; the rest are 'opening_nowhere'.

The two ceilings are ratchets (Q26): lower them when the counts fall, never
raise them. A missing input raises (FileNotFoundError, LookupError): a tool
error, which the CLI reports as exit 2.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from govbudget.jbooks.provenance_pages import (
    book_set,
    fact_anchor,
    narrative_closing,
    narrative_located_at,
    narrative_opening,
    narrative_printed_at,
    normalize_ws,
    page_texts_parallel,
)

# Q26 (owner, 2026-10-04): paged narrative citations whose page prints the
# opening but not the closing are counted, not failed, up to this many — the
# count measured after the relocation (Task 23c Step 6, Task 25c Step 1).
OPENING_ONLY_CEILING = 111
# Pageless narrative citations whose opening some volume of their book set
# prints, but never with the closing words within three pages and the PE
# anchor: an opening alone is not a location (it recurs under other program
# elements — 033016199ca94aa7), so they stay pageless. Same ratchet rule.
PAGELESS_OPENING_SEEN_CEILING = 77

_LOCATED = ("unique", "ambiguous_first")


def _sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _load(site_dir: Path) -> list[tuple]:
    """(fact_id, cited sha, page, resolution, hosted_pdf_url, official_url,
    attached sha, body, pe_bli) per jbook_narrative citation, by fact_id."""
    import duckdb

    cit = site_dir / "citations" / "citations.parquet"
    narr = site_dir / "data" / "jbook_narratives.parquet"
    for path in (cit, narr):
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing")
    con = duckdb.connect()
    try:
        return con.execute(f"""
            select c.fact_id, c.sha256, c.page_number, c.resolution,
                   c.hosted_pdf_url, c.official_url, n.document_sha256, n.body,
                   n.pe_bli
            from read_parquet('{_sql_path(cit)}') c
            left join read_parquet('{_sql_path(narr)}') n on n.fact_id = c.fact_id
            where c.kind = 'jbook_narrative'
            order by c.fact_id
        """).fetchall()
    finally:
        con.close()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_jbook_narratives(site_dir: Path, *, pg_dsn: str,
                            opening_only_ceiling: int = OPENING_ONLY_CEILING,
                            opening_seen_ceiling: int = PAGELESS_OPENING_SEEN_CEILING,
                            texts_for=None) -> dict:
    """Run the check. texts_for(paths) -> {path: raw page texts} (default
    page_texts_parallel). Returns {"ok", "counts", "opening_only",
    "opening_seen", "ceilings", "failures": [(fact_id or "*", reason)]}."""
    import psycopg

    site_dir = Path(site_dir)
    texts_for = texts_for or page_texts_parallel
    rows = _load(site_dir)
    with psycopg.connect(pg_dsn) as con:
        con.execute("set transaction read only")
        sets = {}
        for sha in sorted({r[6] for r in rows if r[6]}):
            hit = con.execute("select id from jbook_documents where sha256 = %s"
                              " order by id limit 1", (sha,)).fetchone()
            if hit is None:
                raise LookupError(f"no jbook_documents row for attached document {sha}")
            sets[sha] = book_set(con, hit[0])
    source: dict[str, Path] = {}
    for vols in sets.values():
        for vol in vols:
            hosted = site_dir / "pdfs" / f"{vol.sha256}.pdf"
            source.setdefault(vol.sha256, hosted if hosted.exists() else Path(vol.file_path))
    bad_bytes: dict[str, str] = {}
    for sha, path in source.items():
        if not path.exists():
            bad_bytes[sha] = f"PDF missing: {path}"
        elif _sha_file(path) != sha:
            bad_bytes[sha] = f"sha256 mismatch: {path} does not hash to {sha}"
    raw = texts_for(sorted(str(p) for s, p in source.items() if s not in bad_bytes))
    norm = {s: [normalize_ws(t) for t in raw[str(p)]]
            for s, p in source.items() if s not in bad_bytes}

    failures: list[tuple[str, str]] = []
    counts = {"citations": len(rows), "paged": 0, "printed": 0, "opening_only": 0,
              "pageless": 0, "opening_seen": 0, "opening_nowhere": 0}
    opening_only: list[str] = []
    opening_seen: list[str] = []
    for fid, sha, page, resolution, hosted, official, attached, body, pe_bli in rows:
        if body is None or attached is None:
            failures.append((fid, "no jbook_narratives row for this citation"))
            continue
        opening, closing = narrative_opening(body), narrative_closing(body)
        if page is not None:
            counts["paged"] += 1
            members = {v.sha256 for v in sets[attached]}
            if resolution not in _LOCATED:
                reason = f"paged citation with resolution {resolution!r}"
            elif sha not in members:
                reason = f"cited volume {sha} is not in the book set of {attached}"
            elif not (site_dir / "pdfs" / f"{sha}.pdf").exists():
                reason = f"cited PDF {sha} is not hosted in pdfs/"
            elif sha in bad_bytes:
                reason = bad_bytes[sha]
            elif not (hosted or "").endswith(f"/{sha}.pdf#page={page}"):
                reason = f"hosted_pdf_url does not name page {page} of {sha}: {hosted!r}"
            elif not (official or "").endswith(f"#page={page}"):
                reason = f"official_url lacks #page={page}: {official!r}"
            elif not 1 <= page <= len(norm[sha]):
                reason = f"page {page} is out of range ({len(norm[sha])} pages)"
            elif opening not in norm[sha][page - 1]:
                reason = f"opening not printed on page {page}: {opening[:60]!r}"
            else:
                reason = None
                if narrative_printed_at(norm[sha], page - 1, opening, closing):
                    counts["printed"] += 1
                else:
                    counts["opening_only"] += 1
                    opening_only.append(fid)
            if reason:
                failures.append((fid, reason))
            continue
        counts["pageless"] += 1
        if sha != attached:
            failures.append((fid, f"pageless citation names {sha},"
                                  f" not its attached document {attached}"))
            continue
        anchor = fact_anchor(pe_bli)
        hit, seen = None, False
        for vol in sets[attached]:
            if vol.sha256 in bad_bytes:
                hit = bad_bytes[vol.sha256]
                break
            texts = norm[vol.sha256]
            for i, text in enumerate(texts):
                if opening and opening in text:
                    seen = True
                    if narrative_located_at(texts, i, opening, closing, anchor):
                        hit = f"pageless, but located at {vol.sha256} page {i + 1}"
                        break
            if hit:
                break
        if hit:
            failures.append((fid, hit))
        elif seen:
            counts["opening_seen"] += 1
            opening_seen.append(fid)
        else:
            counts["opening_nowhere"] += 1
    if counts["opening_only"] > opening_only_ceiling:
        failures.append(("*", f"{counts['opening_only']} opening-only paged citations,"
                              f" above the ceiling of {opening_only_ceiling}"))
    if counts["opening_seen"] > opening_seen_ceiling:
        failures.append(("*", f"{counts['opening_seen']} pageless citations with their"
                              f" opening printed, above the ceiling of {opening_seen_ceiling}"))
    return {"ok": not failures and counts["citations"] > 0, "counts": counts,
            "opening_only": opening_only, "opening_seen": opening_seen,
            "ceilings": {"opening_only": opening_only_ceiling,
                         "opening_seen": opening_seen_ceiling},
            "failures": failures}


def format_report(report: dict) -> list[str]:
    """The lines the CLI and verify-phase5b1 gate 5 print."""
    c, ceil = report["counts"], report["ceilings"]
    lines = [
        f"narrative citations {c['citations']}: paged {c['paged']} (printed"
        f" {c['printed']}, opening_only {c['opening_only']} of at most"
        f" {ceil['opening_only']}); pageless {c['pageless']} (opening printed"
        f" without its closing {c['opening_seen']} of at most {ceil['opening_seen']},"
        f" opening printed nowhere {c['opening_nowhere']})",
    ]
    lines += [f"FAIL {fid}: {reason}" for fid, reason in report["failures"][:20]]
    if len(report["failures"]) > 20:
        lines.append(f"… {len(report['failures']) - 20} more failure(s)")
    return lines
```

- [ ] **Step 4: Wire it into the CLI and verify-phase5b1**

In `src/govbudget/cli.py`, insert directly above the line `    # Gate 3: coverage (non-gating)` (inside `cmd_verify_phase5b1`, after gate 4's `gates_ok = gates_ok and g4_ok`):

```python
    # Gate 5: narrative printed-in, the full population (#195; families
    # piece-1 follow-ups Task 24). Reads Postgres (the book sets) and the PDFs.
    from govbudget.verify_jbook_narratives import format_report, verify_jbook_narratives

    try:
        vj = verify_jbook_narratives(site_dir, pg_dsn=config.PG_DSN)
    except (FileNotFoundError, LookupError) as e:
        g5_ok = False
        print(f"gate 5 narrative printed-in: {e} → FAIL")
    else:
        g5_ok = vj["ok"]
        print(f"gate 5 narrative printed-in: → {'PASS' if g5_ok else 'FAIL'}")
        for line in format_report(vj):
            print(f"  {line}")
    gates_ok = gates_ok and g5_ok

```

Insert directly above `def cmd_verify_phase5e(args) -> None:`:

```python
def cmd_verify_jbook_narratives(args) -> None:
    """#195 (families piece-1 follow-ups Task 24): every jbook_narrative
    citation names a document that prints the passage. Exit 0 PASS, 1 FAIL,
    2 when an input is missing."""
    from govbudget.verify_jbook_narratives import format_report, verify_jbook_narratives

    try:
        report = verify_jbook_narratives(args.site_dir, pg_dsn=args.pg_dsn)
    except (FileNotFoundError, LookupError) as e:
        print(f"verify-jbook-narratives: ERROR — {e}")
        sys.exit(2)
    for line in format_report(report):
        print(line)
    print("verify-jbook-narratives:", "PASS" if report["ok"] else "FAIL")
    sys.exit(0 if report["ok"] else 1)


```

Directly after these two lines

```python
    v5b1 = sub.add_parser("verify-phase5b1", help="phase 5B-1 acceptance gates (citation export)")
    v5b1.set_defaults(func=cmd_verify_phase5b1)
```

insert:

```python
    vjn = sub.add_parser(
        "verify-jbook-narratives",
        help="#195: every jbook_narrative citation names a volume that prints it"
             " (full population; also verify-phase5b1 gate 5)",
    )
    vjn.add_argument("--site-dir", type=Path, default=config.SITE_DIR, dest="site_dir")
    vjn.add_argument("--pg-dsn", default=config.PG_DSN, dest="pg_dsn")
    vjn.set_defaults(func=cmd_verify_jbook_narratives)
```

In `src/govbudget/verify_phase5b1.py`, replace the docstring lines

```python
                          citations exist but none carries page provenance
                          (the pre-5F state).
```

with

```python
                          citations exist but none carries page provenance
                          (the pre-5F state).

  5. narrative printed-in (#195) — govbudget.verify_jbook_narratives, run by
                          the CLI with config.PG_DSN: EVERY jbook_narrative
                          citation names a volume of its book set that prints
                          the passage (paged: opening on the page, closing
                          within three pages, else 'opening_only' up to a
                          ratcheted ceiling; pageless: no volume locates it).
                          Its own pypdf text pass over every book set.
```

In `docs/superpowers/LAUNCH.md` Step 3, replace

```markdown
Expected: `verify-phase5b1: PASS`
```

with

```markdown
Expected: `verify-phase5b1: PASS`

Since #195 (families piece-1 follow-ups, Task 24) gate 5, `gate 5 narrative
printed-in`, also reads Postgres (`GOVBUDGET_PG_DSN`: the book set of each
narrative's document) and the raw J-book PDFs the site does not host, and runs
a pypdf text pass over every narrative book set (about 100 PDFs, a few minutes
on 8 processes). `govbudget verify-jbook-narratives` runs the same check alone.
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_verify_jbook_narratives.py tests/test_verify_phase5b1.py -q 2>&1 | tail -1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1
for f in src/govbudget/cli.py src/govbudget/verify_jbook_narratives.py src/govbudget/verify_phase5b1.py tests/jbooks/test_verify_jbook_narratives.py; do echo "$f $(uvx --offline ruff check --isolated --select F,E9 --output-format concise $f | grep -c ':[0-9]*:[0-9]*:')"; done
```
Expected: `128 passed` (10 new, 118 in `test_verify_phase5b1.py`; checked 2026-10-13 on a scratch copy of the tree with Tasks 23a–23c and this task applied); then the whole suite `… passed` with 0 failed; then the pyflakes counts at their HEAD baselines (W1): `cli.py 5`, `verify_jbook_narratives.py 0`, `verify_phase5b1.py 2`, `test_verify_jbook_narratives.py 0`.

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/verify_jbook_narratives.py GovBudget/tests/jbooks/test_verify_jbook_narratives.py GovBudget/src/govbudget/cli.py GovBudget/src/govbudget/verify_phase5b1.py GovBudget/docs/superpowers/LAUNCH.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(verify): verify-jbook-narratives — every narrative citation names a volume that prints it (#195; verify-phase5b1 gate 5)" -m "Full population, its own pypdf text pass: a paged citation's page prints the opening and the closing follows within three pages (opening_only ratcheted at 111, Q26); no volume of a pageless citation's book set locates it (opening seen without the closing ratcheted at 77, owner-approved <YYYY-MM-DD> at this task's Step 0)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Show the gate red on the export that ships today (read-only)**

The check reads `data/site`, Postgres and `data/raw_docs`, none of which the SAM job writes, so it needs no SAM guard. The live `data/site` is release 1's export (Task 22); release 1 changes no narrative citation, so this is #195's state.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
mkdir -p tmp && uv run --project . python -m govbudget verify-jbook-narratives --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site --pg-dsn postgresql://localhost/govbudget > tmp/fu2-vjn-live-before.txt 2>&1; echo "exit=$?"; head -1 tmp/fu2-vjn-live-before.txt; grep -c 'pageless, but located at' tmp/fu2-vjn-live-before.txt; tail -2 tmp/fu2-vjn-live-before.txt
```
Expected: `exit=1`; `narrative citations 11717: paged 6096 (printed 5757, opening_only 339 of at most 111); pageless 5621 (opening printed without its closing 77 of at most 77, opening printed nowhere 1367)`; `20` (only the first 20 failures print; there are 4,178: 4,177 located-but-pageless plus the ceiling); `… 4158 more failure(s)` and `verify-jbook-narratives: FAIL`. Different counts mean the live state moved since 2026-10-13: stop and re-measure Task 23c Step 6 before Task 25. Nothing is committed in this step; Task 25's proof note quotes these numbers.
