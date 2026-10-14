<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 23b: #195 — the export cites, and hosts, the volume that prints each narrative

**Spec:** §5.6 (Design A, points 2 and 3), §1 ("Facts": no fact ID changes; "Links"), §2.2 Q19 (A). Depends on Task 23a.
**Files:**
- Modify: `src/govbudget/export_site.py` — export step 3, the document copy (anchor on `        # 3. Documents: copy PDFs and workbooks`, line 3054 today); a new helper directly above `def _emit_lineage(` (line 11140 today); one call inserted directly above the comment `    # ROADMAP #29(c) — the /lineage/ identity diagram payload. Built from the` (line 13431 today, after the `lineage_by_pe = _emit_lineage(` call); pass 4h, the narrative citations (anchor on `    with psycopg.connect(dsn) as pg_narr:`, lines 3426–3489 today)
- Modify: `tests/jbooks/test_export_site_5f.py` — new tests appended at the end of the file

Line numbers are hints; anchor on the quoted text. Task 16 (G4) makes `era_grain_fids` a required keyword of `_emit_lineage` and edits its call; nothing here touches that call's arguments, and the new call is anchored on the comment below it.

**Interfaces:**
Consumes: Task 23a's `provenance_pages.printed_document_sha256` (migration 022), `build_narrative_provenance` (writes it), `tests/jbooks/narrative_volumes.py` (`seed_book_set`, `xml_path`, `BODIES`, `VOLUMES`); `tests/jbooks/test_export_site_5f.py`'s own helpers `_export(pg_dsn, tmp_path, *, extend_duckdb=None) -> Path` (exports with `pdf_base_url="https://cdn.example/pdfs"`) and `_narr_citation_row(site, fid) -> dict`; `export_site.fact_id_narrative`.
Produces: in every export, a located `jbook_narrative` citation names the printing volume — `sha256` = `printed_document_sha256` or the attached document's sha, `hosted_pdf_url` = `{pdf_base_url}/{that sha}.pdf#page=N`, `official_url` = that document's `source_url` + `#page=N`, `retrieved_at` = that document's `downloaded_at` — while its `fact_id`, its `jbook_narratives.parquet` row (`document_sha256` = the attached document) and every pageless citation stay as they are; step 3 copies every `superseded` PDF that such a citation names into `pdfs/` (and no other superseded PDF), so `manifest.json` / `site_meta.json` `pdf_count` counts it; the export raises `ValueError` when a citation would name a volume outside the attached document's book set, or a printing volume that is neither `downloaded` nor `superseded`; `export_site._rail_evidence_pages_from_citations(lineage_by_pe: dict, citation_rows: list) -> int` sets each stated lineage edge's sidecar `evidence.page` to its narrative citation's `page_number`.

**Measured now** (2026-10-13, read-only, the 916ae88e export in `data/site` and live Postgres): `manifest.pdf_count` 204 = the PB2017–PB2026 `downloaded` PDFs; none of the 20 `superseded` PB2026 volumes is in `data/site/pdfs` (225 files: the 204 plus 21 receipt books). Task 23a's read-only plan names all 20 superseded volumes as printing volumes (3,479 of its 4,386 changes; Task 23c Step 6 re-measures), so the release-2 export hosts 20 more PDFs, 162,040,168 B (`select sum(bytes) from jbook_documents where status = 'superseded'`). Every one of the 184 stated-edge rail entries in today's sidecars carries the page its narrative citation names (0 differ, checked against `json/citations.json`); after the relocation 22 of the 92 evidence narratives move (21 located, 1 relocated: `652493c1a35f4d2c`, page 332 → 421), so without the rail helper below those sidecar pages would disagree with the citations. Nothing on the site renders `evidence.page` (`site/src/components/lineage/lineage-rail.tsx` reads `fact_id` and `sentence`); `build_lineage_flow` reads only the fact ID.

- [ ] **Step 1: Write the failing export tests**

Append to `tests/jbooks/test_export_site_5f.py`:

```python


# ---------------------------------------------------------------------------
# #195 (families piece-1 follow-ups, Task 23b) — a located narrative cites the
# volume of its book set that prints it, and that volume is hosted
# ---------------------------------------------------------------------------

import datetime as _dt  # noqa: E402

from jbooks.narrative_volumes import BODIES, seed_book_set, xml_path  # noqa: E402


def _book_export(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    assert build_narrative_provenance(pg_dsn) == 6
    return book, _export(pg_dsn, tmp_path)


def _fid(book, key, pe_bli):
    return fact_id_narrative(book["sha"]["BA1"], pe_bli, "mission", xml_path(key))


def test_located_narrative_cites_the_printing_volume(pg_dsn, tmp_path):
    book, site = _book_export(pg_dsn, tmp_path)
    ba2 = book["sha"]["BA2"]
    row = _narr_citation_row(site, _fid(book, "N1", "0605001TST"))
    assert (row["sha256"], row["page_number"], row["resolution"]) == (ba2, 2, "unique")
    assert row["hosted_pdf_url"] == f"https://cdn.example/pdfs/{ba2}.pdf#page=2"
    assert row["official_url"] == "https://example.mil/BA2.pdf#page=2"
    assert _dt.datetime.fromisoformat(row["retrieved_at"]) == _dt.datetime(
        2026, 7, 2, tzinfo=_dt.UTC)
    assert row["xml_path"] == xml_path("N1") and row["pe_bli"] == "0605001TST"
    across = _narr_citation_row(site, _fid(book, "N2", "0605002TST"))
    assert (across["sha256"], across["page_number"]) == (book["sha"]["BA3"], 1)


def test_the_fact_and_its_narrative_row_keep_the_attached_document(pg_dsn, tmp_path):
    book, site = _book_export(pg_dsn, tmp_path)
    narr = site / "data" / "jbook_narratives.parquet"
    rows = dict(duckdb.sql(
        f"select fact_id, document_sha256 from read_parquet('{narr}')").fetchall())
    for key, (pe_bli, _body) in BODIES.items():
        assert rows[_fid(book, key, pe_bli)] == book["sha"]["BA1"]


def test_unlocated_and_attached_narratives_keep_their_citation(pg_dsn, tmp_path):
    book, site = _book_export(pg_dsn, tmp_path)
    ba1 = book["sha"]["BA1"]
    nowhere = _narr_citation_row(site, _fid(book, "N3", "0605003TST"))
    assert (nowhere["sha256"], nowhere["page_number"], nowhere["hosted_pdf_url"]) == (ba1, None, None)
    assert nowhere["official_url"] == "https://example.mil/BA1.pdf"
    own = _narr_citation_row(site, _fid(book, "N4", "0605004TST"))
    assert (own["sha256"], own["page_number"]) == (ba1, 2)
    assert own["hosted_pdf_url"] == f"https://cdn.example/pdfs/{ba1}.pdf#page=2"


def test_superseded_volumes_a_citation_names_are_hosted_and_no_others(pg_dsn, tmp_path):
    book, site = _book_export(pg_dsn, tmp_path)
    hosted = {p.stem for p in (site / "pdfs").glob("*.pdf")}
    assert hosted == {book["sha"][v] for v in ("BA1", "BA2", "BA3", "NAVY")}
    assert json.loads((site / "manifest.json").read_text())["pdf_count"] == 4
    assert json.loads((site / "json" / "site_meta.json").read_text())["pdf_count"] == 4


def test_a_volume_outside_the_book_set_fails_the_export(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    assert build_narrative_provenance(pg_dsn) == 6
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute(
            "update provenance_pages set printed_document_sha256 = %s"
            " where pe_bli = '0605004TST'", (book["sha"]["NAVY"],))
    try:
        _export(pg_dsn, tmp_path)
    except ValueError as e:
        assert "not a volume of" in str(e)
    else:
        raise AssertionError("an export naming another org's volume must fail")


def test_rail_evidence_pages_follow_the_narrative_citations():
    from govbudget.export_site import _rail_evidence_pages_from_citations

    pad = (None,) * 21
    rows = [("f1", "jbook_narrative", None, None, 421) + pad,
            ("f2", "jbook_narrative", None, None, 7) + pad,
            ("f3", "workbook", None, None, 9) + pad]
    lineage = {
        "P1": {"rail": {
            "predecessors": [{"pe": "P0", "evidence": {"fact_id": "f1", "page": 332, "sentence": "s"}}],
            "successors": [{"pe": "P2", "evidence": None},
                           {"pe": "P3", "evidence": {"fact_id": "f2", "page": None, "sentence": "t"}}],
        }},
        "P9": {"family": {"id": 1}},
    }
    assert _rail_evidence_pages_from_citations(lineage, rows) == 2
    assert lineage["P1"]["rail"]["predecessors"][0]["evidence"]["page"] == 421
    assert lineage["P1"]["rail"]["successors"][1]["evidence"]["page"] == 7
    assert lineage["P1"]["rail"]["successors"][0]["evidence"] is None
    assert _rail_evidence_pages_from_citations(lineage, rows) == 0
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_5f.py -q 2>&1 | tail -8`
Expected: `4 failed, 15 passed` (19 tests: 12 at HEAD, Task 12's `test_route_safe_alias_sidecar_names_its_printed_code`, and this step's 6). The three export tests that look at a located narrative's citation, `pdfs/` or a foreign volume fail on their assertions (`sha256` is still BA1's sha; the hosted set lacks BA2 and BA3 and `pdf_count` is 2; `AssertionError: an export naming another org's volume must fail`), and the rail test fails with `ImportError: cannot import name '_rail_evidence_pages_from_citations'`. The 13 existing tests (Task 12's included), `test_unlocated_and_attached_narratives_keep_their_citation` and `test_the_fact_and_its_narrative_row_keep_the_attached_document` pass before and after (checked 2026-10-13 on a scratch copy of the tree with Task 23a applied).

- [ ] **Step 3: Host the printing volumes (export step 3)**

In `src/govbudget/export_site.py`, replace

```python
        # -----------------------------------------------------------------------
        # 3. Documents: copy PDFs and workbooks
        # -----------------------------------------------------------------------
        doc_rows = pg.execute(
            """
            select sha256, file_path, source_url, downloaded_at
            from jbook_documents
            where status = 'downloaded' and sha256 is not null
            order by sha256
            """
        ).fetchall()
```

with

```python
        # -----------------------------------------------------------------------
        # 3. Documents: copy PDFs and workbooks
        # -----------------------------------------------------------------------
        # #195 (families piece-1 follow-ups, Task 23b): a narrative's provenance
        # row may name the SUPERSEDED volume of its book set that prints it
        # (printed_document_sha256). Every such volume a citation of THIS export
        # names is copied too, so its #page=N anchor opens a hosted PDF; a
        # superseded volume no citation names stays unhosted.
        _cited_narr_keys = {
            (r[9], r[1], r[3], r[6]) for r in narr_rows_with_fid if r[0] and r[6]
        }
        printed_volume_shas = sorted({
            printed
            for (p_sha, p_pe, p_kind, p_xml, printed) in pg.execute(
                """
                select document_sha256, pe_bli, narrative_kind, xml_path,
                       printed_document_sha256
                from provenance_pages
                where target_kind = 'narrative'
                  and printed_document_sha256 is not null
                  and page_number is not null
                  and resolution in ('unique', 'ambiguous_first')
                """
            ).fetchall()
            if (p_sha, p_pe, p_kind, p_xml) in _cited_narr_keys
        })
        doc_rows = pg.execute(
            """
            select sha256, file_path, source_url, downloaded_at
            from jbook_documents
            where sha256 is not null
              and (status = 'downloaded'
                   or (status = 'superseded' and sha256 = any(%s)))
            order by sha256
            """,
            (printed_volume_shas,),
        ).fetchall()
        _unhosted = sorted(set(printed_volume_shas) - {r[0] for r in doc_rows})
        if _unhosted:
            raise ValueError(
                f"#195: {len(_unhosted)} narrative printing volume(s) are neither"
                f" downloaded nor superseded documents: {_unhosted[:5]}"
            )
```

(`narr_rows_with_fid` rows are `(fid, pe_bli, pn, kind, title, body, xml_path, org, fy, sha)`, built in step 2b of the same `with` block, so indices 9, 1, 3, 6 are the identity `fact_id_narrative` hashes.)

- [ ] **Step 4: Cite the printing volume (pass 4h)**

Replace

```python
    with psycopg.connect(dsn) as pg_narr:
        narr_doc_lookup = {
            r[0]: (r[1], r[2])
            for r in pg_narr.execute(
                """
                select distinct on (sha256) sha256, source_url, downloaded_at
                from jbook_documents
                where sha256 is not null
                order by sha256, id
                """
            ).fetchall()
        }
        narr_prov: dict[tuple, tuple] = {}
        for (p_sha, p_pe, p_kind, p_xml, page_number, x0, x1, top_pt,
             bottom_pt, page_width, page_height, resolution) in pg_narr.execute(
            """
            select document_sha256, pe_bli, narrative_kind, xml_path,
                   page_number, x0, x1, top_pt, bottom_pt,
                   page_width, page_height, resolution
            from provenance_pages
            where target_kind = 'narrative'
            """
        ).fetchall():
            if resolution in ("unique", "ambiguous_first") and page_number is not None:
                narr_prov[(p_sha, p_pe, p_kind, p_xml)] = (
                    int(page_number),
                    float(x0), float(x1), float(top_pt), float(bottom_pt),
                    float(page_width), float(page_height), resolution,
                )

    for (fid, pe_bli, pn, kind, title, body, xml_path, org, fy, sha) in narr_rows_with_fid:
        if fid is None or not xml_path:
            continue  # skip rows without a resolvable xml_path
        src_url, dl_at = narr_doc_lookup.get(sha, (None, None))
        official_url = src_url or None
        ret_at = dl_at.isoformat() if dl_at else None
        hit = narr_prov.get((sha, pe_bli, kind, xml_path))
        if hit is not None:
            (page_number, x0, x1, top_pt, bottom_pt,
             page_width, page_height, resolution) = hit
            hosted_pdf_url = f"{pdf_base_url}/{sha}.pdf#page={page_number}"
            if official_url:
                official_url = f"{official_url}#page={page_number}"
        else:
            page_number = x0 = x1 = top_pt = bottom_pt = None
            page_width = page_height = resolution = None
            hosted_pdf_url = None
        citation_rows.append((
            fid, "jbook_narrative", None,  # fact_id, kind, units
            None,          # amount_text (narrative locations are prose, not amounts)
            page_number, x0, x1, top_pt, bottom_pt, page_width, page_height,
            resolution,    # 'unique' | 'ambiguous_first' | None (pageless)
            None,   # sheet
            None,   # cells
            None,   # amount_thousands
            sha,    # sha256 (document fingerprint for integrity check)
            hosted_pdf_url,
            official_url,  # official_url (#page=N when located)
            xml_path,      # xml_path (J-book XML locator)
            ret_at,        # retrieved_at
            None, None, None, None,  # formula, inputs, query_body, recorded_value
            pe_bli, None, None,  # pe_bli, scenario, amount_type
        ))
```

with

```python
    with psycopg.connect(dsn) as pg_narr:
        narr_doc_lookup = {
            r[0]: (r[1], r[2], (r[3], r[4], r[5]))
            for r in pg_narr.execute(
                """
                select distinct on (sha256) sha256, source_url, downloaded_at,
                       fiscal_year, org, exhibit_family
                from jbook_documents
                where sha256 is not null
                order by sha256, id
                """
            ).fetchall()
        }
        narr_prov: dict[tuple, tuple] = {}
        for (p_sha, p_pe, p_kind, p_xml, page_number, x0, x1, top_pt,
             bottom_pt, page_width, page_height, resolution,
             printed_sha) in pg_narr.execute(
            """
            select document_sha256, pe_bli, narrative_kind, xml_path,
                   page_number, x0, x1, top_pt, bottom_pt,
                   page_width, page_height, resolution,
                   printed_document_sha256
            from provenance_pages
            where target_kind = 'narrative'
            """
        ).fetchall():
            if resolution in ("unique", "ambiguous_first") and page_number is not None:
                narr_prov[(p_sha, p_pe, p_kind, p_xml)] = (
                    int(page_number),
                    float(x0), float(x1), float(top_pt), float(bottom_pt),
                    float(page_width), float(page_height), resolution,
                    printed_sha or p_sha,
                )

    for (fid, pe_bli, pn, kind, title, body, xml_path, org, fy, sha) in narr_rows_with_fid:
        if fid is None or not xml_path:
            continue  # skip rows without a resolvable xml_path
        hit = narr_prov.get((sha, pe_bli, kind, xml_path))
        # #195 (Task 23b): a located narrative cites the volume that PRINTS it
        # (printed_document_sha256, else the attached document) — its sha256,
        # hosted copy, official URL and retrieval time. The fact_id keeps
        # hashing the attached document (fact_id_narrative), so lineage and
        # verify-lineage see the same identities.
        cited_sha = hit[8] if hit is not None else sha
        if cited_sha != sha and (
                narr_doc_lookup.get(cited_sha, (None, None, None))[2]
                != narr_doc_lookup.get(sha, (None, None, None))[2]):
            raise ValueError(
                f"#195: narrative {fid} is located in {cited_sha}, which is not"
                f" a volume of {sha}'s book set (edition, org, exhibit family)"
            )
        src_url, dl_at, _book = narr_doc_lookup.get(cited_sha, (None, None, None))
        official_url = src_url or None
        ret_at = dl_at.isoformat() if dl_at else None
        if hit is not None:
            (page_number, x0, x1, top_pt, bottom_pt,
             page_width, page_height, resolution, _printed) = hit
            hosted_pdf_url = f"{pdf_base_url}/{cited_sha}.pdf#page={page_number}"
            if official_url:
                official_url = f"{official_url}#page={page_number}"
        else:
            page_number = x0 = x1 = top_pt = bottom_pt = None
            page_width = page_height = resolution = None
            hosted_pdf_url = None
        citation_rows.append((
            fid, "jbook_narrative", None,  # fact_id, kind, units
            None,          # amount_text (narrative locations are prose, not amounts)
            page_number, x0, x1, top_pt, bottom_pt, page_width, page_height,
            resolution,    # 'unique' | 'ambiguous_first' | None (pageless)
            None,   # sheet
            None,   # cells
            None,   # amount_thousands
            cited_sha,  # sha256: the printing volume (#195), else the attached document
            hosted_pdf_url,
            official_url,  # official_url (#page=N when located)
            xml_path,      # xml_path (J-book XML locator)
            ret_at,        # retrieved_at
            None, None, None, None,  # formula, inputs, query_body, recorded_value
            pe_bli, None, None,  # pe_bli, scenario, amount_type
        ))
```

- [ ] **Step 5: Keep the lineage rail's evidence page on the citation's page**

Insert directly above `def _emit_lineage(`:

```python
def _rail_evidence_pages_from_citations(lineage_by_pe: dict, citation_rows: list) -> int:
    """#195 (families piece-1 follow-ups, Task 23b): a stated lineage edge's
    evidence page is the page its narrative citation names.

    program_lineage.evidence_page was copied from provenance_pages when the
    lineage was built, and it names a page of the ATTACHED volume; once a
    narrative is located in another volume (or newly located), the citation's
    page is the true one and the sidecar must not disagree with it. Rewrites
    the rail entries' evidence pages in place; returns how many changed.
    citation_rows are export_site's 27-column citation tuples (index 4 is
    page_number).
    """
    pages = {row[0]: row[4] for row in citation_rows if row[1] == "jbook_narrative"}
    changed = 0
    for block in lineage_by_pe.values():
        rail = block.get("rail") or {}
        for side in ("predecessors", "successors"):
            for entry in rail.get(side) or []:
                evidence = entry.get("evidence")
                if evidence and evidence.get("page") != pages.get(evidence["fact_id"]):
                    evidence["page"] = pages.get(evidence["fact_id"])
                    changed += 1
    return changed


```

Then insert directly above the line `    # ROADMAP #29(c) — the /lineage/ identity diagram payload. Built from the` (it follows the `lineage_by_pe = _emit_lineage(` call):

```python
    # #195 (Task 23b): rail evidence pages follow the narrative citations.
    _rail_pages_moved = _rail_evidence_pages_from_citations(lineage_by_pe, citation_rows)
    if _rail_pages_moved:
        print(
            f"lineage: {_rail_pages_moved} rail evidence page(s) taken from the"
            " narrative citations (#195: a narrative located in another volume"
            " or newly located)"
        )

```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_5f.py tests/jbooks/test_export_site_pg.py tests/jbooks/test_export_lineage.py tests/jbooks/test_narrative_book_set.py tests/test_verify_phase5b1.py -q 2>&1 | tail -2`
Expected: `… passed` with 0 failed (19 in `test_export_site_5f.py`).

Then the whole suite and pyflakes on the touched module against its HEAD baseline (W1: `export_site.py` carries 10 findings at HEAD, measured 2026-10-13 with this command on the unmodified file; the edit adds none):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 --output-format concise src/govbudget/export_site.py tests/jbooks/test_export_site_5f.py | grep -c ':[0-9]*:[0-9]*:'
```
Expected: `… passed` with 0 failed; then `10`.

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/export_site.py GovBudget/tests/jbooks/test_export_site_5f.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(export): a located narrative cites the volume that prints it, and that volume is hosted (#195)" -m "Pass 4h takes sha256, the hosted and official #page=N URLs and retrieved_at from printed_document_sha256 when it is set; fact IDs still hash the attached document. Step 3 copies each superseded volume a citation names. Lineage rail evidence pages follow the citations." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
