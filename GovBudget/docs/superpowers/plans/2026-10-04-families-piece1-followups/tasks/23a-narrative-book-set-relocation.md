<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 23a: #195 — migration 022 and the book-set relocation in `provenance_pages`

**Spec:** §5.6 (Design A, points 1 and 4: the shared printed-in rule), §1 ("Facts": every fact ID keeps its identity), §2.2 Q19 (A), §2.3 Q26. Task 23 is split in three for review: 23a (this file: schema and library), 23b (the export cites and hosts the printing volume), 23c (the transactional write script and the read-only measurement on the live database). All three land after Task 22 has published release 1; none of them writes the live database or the live lake (Task 26 does, after Task 25's rehearsal).
**Files:**
- Create: `migrations/022_provenance_pages_printed_document.sql`
- Create: `tests/jbooks/test_migration_022.py`
- Create: `tests/jbooks/narrative_volumes.py` (the synthetic book set Tasks 23a, 23b, 23c and 24 share)
- Create: `tests/jbooks/test_narrative_book_set.py`
- Modify: `src/govbudget/jbooks/provenance_pages.py` — the import block (anchor on `from itertools import groupby`), a new section inserted directly above `def build_narrative_provenance(` (line 489 today), and `build_narrative_provenance` itself (lines 489–587 today, the end of the file)

Line numbers are hints; anchor on the quoted text.

**Interfaces:**
Consumes: `govbudget.jbooks.db.migrate(dsn=None) -> list[str]` (applies `migrations/*.sql` in name order, tracked by file name in `schema_migrations`); the `pg_dsn` session fixture of `tests/jbooks/conftest.py` (creates `govbudget_test` on `GOVBUDGET_TEST_PG_DSN` and runs `migrate`); `tests/pdf_factory.make_pdf(path, pages)`; the module's existing helpers `_page_texts(pdf_path) -> list[str]`, `_preferred_candidates`, `_find_word_span`, `_first_line_bbox`, `_resolve_narrative`, `normalize_ws`, `narrative_opening`, `fact_anchor`, `NARRATIVE_OPENING_WORDS = 12`.
Produces:
- Postgres: `provenance_pages.printed_document_sha256 text` (nullable; null = the attached `document_sha256`), constraint `provenance_pages_printed_document_shape`. No backfill.
- `govbudget.jbooks.provenance_pages`: `NARRATIVE_CLOSING_WORDS = 12`; `NARRATIVE_CLOSING_SPAN_PAGES = 3`; `narrative_closing(body: str, n_words: int = 12) -> str`; `narrative_printed_at(norm_texts: list[str], page_idx: int, opening: str, closing: str) -> bool`; `narrative_located_at(norm_texts, page_idx, opening, closing, anchor: str | None) -> bool`; `@dataclass(frozen=True) Volume(document_id: int, sha256: str, file_path: str, status: str, title: str)`; `book_set(con, document_id: int) -> list[Volume]`; `page_texts_parallel(paths: list[str], *, workers: int | None = None) -> dict[str, list[str]]`; `resolve_printed_narrative(volumes, texts, plumber_for, *, opening, closing, pe_bli, project_number, exhibit_family, words_cache) -> dict | None` (keys `page_number, x0, x1, top_pt, bottom_pt, page_width, page_height, resolution, candidate_pages, search_text, printed_sha256`); `RELOCATION_COLUMNS = ("page_number", "x0", "x1", "top_pt", "bottom_pt", "page_width", "page_height", "resolution", "candidate_pages", "printed_document_sha256")`; `same_location(a: dict, b: dict) -> bool` (relocation columns equal, the box within 1e-6 pt); `plan_narrative_relocations(con, *, fiscal_years: list[int] | None = None, texts_for=None, printed_column: bool = True, log=print) -> dict` returning `{"changes": [{"id": int, "fact_key": [document_sha256, pe_bli, kind, xml_path], "kind": "located" | "relocated", "before": {col: value}, "after": {col: value}}], "counts": {"rows", "kept", "located", "relocated", "opening_only", "unresolved"}, "printed_volumes": {sha256: {"title", "status", "rows"}}}`. `build_narrative_provenance` keeps its signature and now writes `printed_document_sha256`.
- `tests/jbooks/narrative_volumes.py`: `R2`, `BODIES`, `PAGES`, `VOLUMES`, `seed_book_set(pg_dsn, tmp_path) -> {"sha": {vol: str}, "doc": {vol: int}, "path": {vol: Path}}`, `seed_pre_195_rows(pg_dsn, book) -> None`.

**Measured now** (2026-10-13, read-only: live Postgres with `set transaction read only`, `data/site` of the 916ae88e export, pypdf 6.13.2 page texts of the 103 PDFs in the book sets of the 82 documents the export's narrative citations name; scratch scripts `census.py`, `proto/` under `.superpowers/sdd/2026-10-04-piece1-followups/work/g6/`):
- `provenance_pages` holds 11,961 narrative rows (5,439 `unique`, 657 `ambiguous_first`, 5,865 `unresolved`); the 11,679 PB2026 narratives the export cites all have one (5,422 / 656 / 5,601). `schema_migrations` ends at `021_budget_lines_line_item_code.sql`, so the next file is 022 (no task before this one adds a migration: design §4.4 "No migration").
- PB2026 holds 82 PDF documents, 20 of them `superseded` (162,040,168 B, none hosted in `data/site/pdfs`). The 20 sit in 8 groups of identical master-XML sha (`service_fetch._picked_master_sha`): Army OPA (346 kept; 347 BA1, 348 BA2), Army RDT&E Vol 1 (351; 352), Vol 2 (353; 354), Vol 3 (355; 356–358), Vol 4 (359; 360–362), AF Aircraft (407; 408), AF RDT&E (412; 413–415), Navy APN (330; 331, 332), Navy OPN (333; 334–337).
- **Why the set is the book set, not the master-XML group (contract issue G6-1).** Army RDT&E Vol 1 BA1 (doc 344, master `U_RDTE_MJB_2506261522…`, 3,779,186 B) and BA2 (doc 351, master `…2506271419…`, 3,780,329 B) embed two regenerations of one master: each holds the same 1,189 live narratives, 1,207 PB2026 narrative pairs share (pe_bli, kind, body) across documents, and `/program/0601102A/` carries 106 + 106 of them. The 108 pageless records of 0601102A that design §5.6's weight estimate counts are attached to 351 and printed only in 344, which is a different master sha. Searching only identical-sha volumes would leave them (and the other 721 "printed in a different hosted volume") pageless.
- The census over the 11,717 exported narrative citations, with the rule this task implements (a page **prints** a narrative when its normalized text holds the first 12 words and pages p..p+2 joined hold the last 12; a **new location** also needs the page to print the PE/BLI anchor):
  - paged PB2026 6,078: 5,739 printed where cited; 339 not (design Q26's 339); of those, 228 have a located page elsewhere (180 in the same volume, 48 in another volume of the master group) and 111 have none (Q26's `opening_only` 111). Without the anchor requirement the split is 230 / 109, so the anchor is what reproduces Q26's 228 / 111.
  - pageless PB2026 5,601: 4,157 are located in their book set (2,996 in a superseded volume of the same master group, 440 in another superseded volume, 721 in a hosted volume of another master); 1,444 stay pageless — 1,367 whose opening no volume of the set prints and 77 whose opening a volume prints without the closing words within three pages (contract issue G6-2: design §5.6 counts these 77 as printed and expects "about 1,370").
  - other editions (the lineage-evidence citations): 18 paged, all printed; 20 pageless, all located in their book set — 19 of them in their own volume, because they have **no** `provenance_pages` row at all (never built), and one (`906bcdda2a0660d1`, PB2019) with an `unresolved` row, located in another hosted volume (contract issue G6-3; Task 25 and Task 26 run `jbooks narrative-provenance --lineage-evidence` for the 19).
- F-15: `e7d5bcfb4a30f458` (the F015E0 note receipt, `NOTE_RECEIPTS` pins page 71 of `528d1441…`, Vol I) is printed where cited and is kept; `033016199ca94aa7` (design §5.6's example) is one of the 48 relocated to another volume.

- [ ] **Step 1: Write the failing migration test**

Create `tests/jbooks/test_migration_022.py`:

```python
"""Migration 022 (#195; families piece-1 follow-ups design §5.6):
provenance_pages.printed_document_sha256, the volume that prints a narrative
row's passage when it is not the attached document.

The session fixture (tests/jbooks/conftest.py) built the test database through
migrate(), so the column and its constraint exist; each test runs in a
transaction that is rolled back.
"""
import psycopg
import pytest

from govbudget.jbooks.db import MIGRATIONS_DIR

SQL_PATH = MIGRATIONS_DIR / "022_provenance_pages_printed_document.sql"
COMMENT = (
    "sha256 of the volume of the same book set that prints this narrative row's"
    " passage, when it is not document_sha256 (#195); page_number and the box"
    " refer to it; null = document_sha256"
)
A, B = "a" * 64, "b" * 64


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _narrative(con, printed, *, document=A):
    con.execute(
        "insert into provenance_pages (target_kind, document_sha256, pe_bli,"
        " narrative_kind, xml_path, amount_text, resolution, printed_document_sha256)"
        " values ('narrative', %s, 'PE022', 'mission', 'ProgramElement[0]', 'x',"
        " 'unique', %s)", (document, printed))


def test_022_adds_a_commented_nullable_text_column(con):
    assert SQL_PATH.exists()
    assert con.execute(
        "select data_type, is_nullable from information_schema.columns"
        " where table_name = 'provenance_pages'"
        " and column_name = 'printed_document_sha256'"
    ).fetchall() == [("text", "YES")]
    assert con.execute(
        "select col_description('provenance_pages'::regclass, attnum)"
        " from pg_attribute where attrelid = 'provenance_pages'::regclass"
        " and attname = 'printed_document_sha256'"
    ).fetchone()[0] == COMMENT


def test_022_a_narrative_row_may_name_another_volume(con):
    _narrative(con, None)
    _narrative(con, B, document="c" * 64)
    assert con.execute(
        "select count(*) from provenance_pages where printed_document_sha256 = %s", (B,)
    ).fetchone()[0] == 1


@pytest.mark.parametrize("printed", ["b" * 63, "B" * 64, A])
def test_022_the_printing_volume_is_another_lowercase_sha(con, printed):
    with pytest.raises(psycopg.errors.CheckViolation):
        _narrative(con, printed)


def test_022_amount_rows_never_name_a_printing_volume(con):
    with pytest.raises(psycopg.errors.CheckViolation):
        con.execute(
            "insert into provenance_pages (target_kind, document_sha256, pe_bli,"
            " scenario, amount_millions, amount_text, resolution,"
            " printed_document_sha256) values ('amount', %s, 'PE022', 'BY1', 1.0,"
            " '1.000', 'unique', %s)", (A, B))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_migration_022.py -q 2>&1 | tail -3`
Expected: `6 failed` (the first on `assert SQL_PATH.exists()`; the others with `psycopg.errors.UndefinedColumn: column "printed_document_sha256" of relation "provenance_pages" does not exist`).

- [ ] **Step 3: Write the migration**

Create `migrations/022_provenance_pages_printed_document.sql`:

```sql
-- 022: the volume that prints a narrative (#195; families piece-1 follow-ups,
-- docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md §5.6).
--
-- service_fetch.dedup_service_master_dups keeps one volume per embedded master
-- XML and marks the rest superseded, and every narrative of that master is
-- attached to the kept volume, which prints only its own budget activities.
-- A narrative row's page and box refer to printed_document_sha256 when it is
-- set (another volume of the same book set, superseded volumes included) and
-- to document_sha256 otherwise. The row's identity (document_sha256, pe_bli,
-- narrative_kind, xml_path) and fact_id_narrative do not change. No backfill:
-- null keeps every existing row's meaning.
alter table provenance_pages add column printed_document_sha256 text;
comment on column provenance_pages.printed_document_sha256 is
  'sha256 of the volume of the same book set that prints this narrative row''s passage, when it is not document_sha256 (#195); page_number and the box refer to it; null = document_sha256';
alter table provenance_pages add constraint provenance_pages_printed_document_shape
  check (printed_document_sha256 is null
         or (target_kind = 'narrative'
             and printed_document_sha256 ~ '^[0-9a-f]{64}$'
             and printed_document_sha256 <> document_sha256));
```

Run the Step 2 command again. Expected: `6 passed`. Then the other migration tests, which rebuild nothing but share the fixture: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_migration_003.py tests/jbooks/test_migration_021.py tests/jbooks/test_provenance_pages.py -q 2>&1 | tail -1` — expected `… passed` and 0 failed (the narrative builder tests still pass: the old builder never names the column).

- [ ] **Step 4: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/migrations/022_provenance_pages_printed_document.sql GovBudget/tests/jbooks/test_migration_022.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): migration 022 — provenance_pages.printed_document_sha256, the volume that prints a narrative (#195)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Write the shared synthetic book set and the failing library tests**

Create `tests/jbooks/narrative_volumes.py`:

```python
"""A synthetic PB2026 book set for the #195 tests (Tasks 23a, 23b, 23c, 24).

Org 'A' RDT&E, fiscal year 2026: volume BA1 is the downloaded book every
narrative is attached to (its master XML holds all six narratives); BA2, BA3
and BA4 are superseded volumes of the same book set; an org 'N' book is
outside the set. Each narrative and where its words are printed:

  N1 0605001TST  BA1 p1 prints only the opening; BA2 p2 prints it whole
                 -> stored on BA1 p1 by the pre-#195 builder; relocated to BA2 p2
  N2 0605002TST  BA3 p1-p2 prints it whole across the page break
                 -> stored unresolved; located on BA3 p1
  N3 0605003TST  printed nowhere -> stays unresolved
  N4 0605004TST  BA1 p2 prints it whole -> kept
  N5 0605005TST  BA1 p3 prints only the opening; nothing prints the closing
                 -> stays on BA1 p3 (opening_only)
  N6 0605006TST  only the org 'N' book prints it -> stays unresolved
  BA4 prints none of them and is never cited.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg

from pdf_factory import make_pdf

R2 = "Exhibit R-2, RDT&E Budget Item Justification"

BODIES = {
    "N1": ("0605001TST", "The Alpha program fields a new radar for the fleet. It replaces three"
                         " legacy sets and the work continues through the final test event in FY 2027."),
    "N2": ("0605002TST", "The Bravo effort builds a test range for hypersonic flight trials. Funding"
                         " in FY 2026 completes the range control center and the first two telemetry sites."),
    "N3": ("0605003TST", "The Charlie study is described in a classified annex that is not part of"
                         " this book and no page prints its text at all anywhere in any volume."),
    "N4": ("0605004TST", "The Delta line buys spares for the training fleet. The quantity rises in FY"
                         " 2026 because two squadrons convert to the new aircraft type."),
    "N5": ("0605005TST", "The Echo program upgrades the cockpit displays on the trainer. Work in FY"
                         " 2026 integrates the software and starts the qualification test series."),
    "N6": ("0605006TST", "The Foxtrot program buys night vision sets for the reserve units. The FY"
                         " 2026 request completes the second lot and closes out the contract."),
}

PAGES = {
    "BA1": [
        [R2, "PE 0605001TST / ALPHA",
         "The Alpha program fields a new radar for the fleet. It replaces", "three legacy sets."],
        [R2, "PE 0605004TST / DELTA",
         "The Delta line buys spares for the training fleet. The quantity rises",
         "in FY 2026 because two squadrons convert to the new aircraft type."],
        [R2, "PE 0605005TST / ECHO",
         "The Echo program upgrades the cockpit displays on the trainer. Work in FY",
         "2026 integrates the software."],
    ],
    "BA2": [
        [R2, "PE 0605009TST / OTHER", "Unrelated text on the first page of the second volume."],
        [R2, "PE 0605001TST / ALPHA",
         "The Alpha program fields a new radar for the fleet. It replaces",
         "three legacy sets and the work continues through the final test", "event in FY 2027."],
    ],
    "BA3": [
        [R2, "PE 0605002TST / BRAVO",
         "The Bravo effort builds a test range for hypersonic flight trials.", "Funding in FY 2026"],
        ["completes the range control center and the first two", "telemetry sites."],
    ],
    "BA4": [[R2, "PE 0605008TST / GOLF", "Nothing here is cited by any narrative."]],
    "NAVY": [
        [R2, "PE 0605006TST / FOXTROT",
         "The Foxtrot program buys night vision sets for the reserve units. The FY",
         "2026 request completes the second lot and closes out the contract."],
    ],
}

# (org, status, title) per volume; BA1 is the attached, downloaded book.
VOLUMES = {
    "BA1": ("A", "downloaded", "Book BA1"),
    "BA2": ("A", "superseded", "Book BA2"),
    "BA3": ("A", "superseded", "Book BA3"),
    "BA4": ("A", "superseded", "Book BA4"),
    "NAVY": ("N", "downloaded", "Navy book"),
}


def xml_path(key: str) -> str:
    return f"ProgramElement[{list(BODIES).index(key)}]/Narrative[0]"


def seed_book_set(pg_dsn: str, tmp_path: Path) -> dict:
    """Write the five PDFs, register them, attach the six narratives to BA1.

    Returns {"sha": {volume: sha256}, "doc": {volume: id}, "path": {volume: Path}}.
    Volume n (1-based, in VOLUMES order) was downloaded 2026-07-0n.
    """
    out = {"sha": {}, "doc": {}, "path": {}}
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        for n, (vol, (org, status, title)) in enumerate(VOLUMES.items(), start=1):
            path = tmp_path / f"{vol}.pdf"
            make_pdf(path, PAGES[vol])
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            doc_id = con.execute(
                "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
                " source_url, file_path, sha256, bytes, downloaded_at, has_embedded_xml,"
                " status) values (%s, 'rdte', 2026, %s, %s, %s, %s, %s, %s, true, %s)"
                " returning id",
                (org, title, f"https://example.mil/{vol}.pdf", str(path), sha,
                 path.stat().st_size, f"2026-07-0{n}T00:00:00+00:00", status),
            ).fetchone()[0]
            out["sha"][vol], out["doc"][vol], out["path"][vol] = sha, doc_id, path
        run_id = con.execute(
            "insert into extraction_runs (document_id, tier, tool_versions)"
            " values (%s, 1, '{}') returning id", (out["doc"]["BA1"],)).fetchone()[0]
        for key, (pe_bli, body) in BODIES.items():
            con.execute(
                "insert into detail_narratives (extraction_run_id, document_id, pe_bli,"
                " kind, title, body, xml_path) values (%s, %s, %s, 'mission', %s, %s, %s)",
                (run_id, out["doc"]["BA1"], pe_bli, key, body, xml_path(key)),
            )
    return out


def seed_pre_195_rows(pg_dsn: str, book: dict) -> None:
    """The rows the pre-#195 builder stored: each narrative resolved against
    BA1 alone by its opening (find_narrative_page, the old single-volume rule)."""
    from govbudget.jbooks.provenance_pages import find_narrative_page

    with psycopg.connect(pg_dsn, autocommit=True) as con:
        for key, (pe_bli, body) in BODIES.items():
            hit = find_narrative_page(book["path"]["BA1"], pe_bli=pe_bli, body=body,
                                      exhibit_family="rdte")
            con.execute(
                "insert into provenance_pages (target_kind, document_sha256, pe_bli,"
                " narrative_kind, xml_path, amount_text, page_number, x0, x1, top_pt,"
                " bottom_pt, page_width, page_height, resolution, candidate_pages)"
                " values ('narrative', %s, %s, 'mission', %s, %s, %s, %s, %s, %s, %s,"
                " %s, %s, %s, %s)",
                (book["sha"]["BA1"], pe_bli, xml_path(key), hit["search_text"],
                 hit["page_number"], hit["x0"], hit["x1"], hit["top_pt"],
                 hit["bottom_pt"], hit["page_width"], hit["page_height"],
                 hit["resolution"], hit["candidate_pages"]),
            )
```

Create `tests/jbooks/test_narrative_book_set.py`:

```python
"""#195: a narrative is cited to the volume of its book set that prints it
(families piece-1 follow-ups design §5.6; Task 23a)."""
from __future__ import annotations

from pathlib import Path

import psycopg

from govbudget.jbooks.provenance_pages import (
    NARRATIVE_CLOSING_SPAN_PAGES,
    NARRATIVE_CLOSING_WORDS,
    RELOCATION_COLUMNS,
    _page_texts,
    book_set,
    build_narrative_provenance,
    narrative_closing,
    narrative_located_at,
    narrative_printed_at,
    page_texts_parallel,
    plan_narrative_relocations,
)
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows

ROW_STATE = ("select id, page_number, x0, resolution, candidate_pages,"
             " printed_document_sha256 from provenance_pages order by id")


def _plan(pg_dsn, **kwargs):
    with psycopg.connect(pg_dsn) as con:
        return plan_narrative_relocations(con, log=lambda *_: None, **kwargs)


def test_closing_is_the_last_twelve_words_whitespace_normalized():
    assert (NARRATIVE_CLOSING_WORDS, NARRATIVE_CLOSING_SPAN_PAGES) == (12, 3)
    body = " ".join(f"w{i}" for i in range(1, 31))
    assert narrative_closing(body) == " ".join(f"w{i}" for i in range(19, 31))
    assert narrative_closing("a\n b\t c") == "a b c"
    assert narrative_closing("   ") == ""


def test_printed_at_needs_the_opening_on_the_page_and_the_closing_within_three_pages():
    pages = ["intro OPEN words here", "middle", "more CLOSE", "late END"]
    assert narrative_printed_at(pages, 0, "OPEN words", "more CLOSE")
    assert narrative_printed_at(pages, 0, "OPEN words", "here middle more")  # across page breaks
    assert not narrative_printed_at(pages, 0, "OPEN words", "late END")      # fourth page
    assert not narrative_printed_at(pages, 1, "OPEN words", "more CLOSE")    # opening elsewhere
    assert not narrative_printed_at(pages, 7, "OPEN words", "more CLOSE")    # no such page
    assert not narrative_printed_at(pages, 0, "", "more CLOSE")


def test_located_at_also_needs_the_anchor_on_the_opening_page():
    pages = ["PE 0605001TST intro OPEN words", "more CLOSE"]
    assert narrative_located_at(pages, 0, "OPEN words", "more CLOSE", "0605001TST")
    assert not narrative_located_at(pages, 0, "OPEN words", "more CLOSE", "0605002TST")
    assert not narrative_located_at(pages, 0, "OPEN words", "more CLOSE", None)


def test_book_set_is_edition_org_and_family_attached_volume_first(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    with psycopg.connect(pg_dsn) as con:
        vols = book_set(con, book["doc"]["BA1"])
        from_ba3 = [v.title for v in book_set(con, book["doc"]["BA3"])]
    assert [v.title for v in vols] == ["Book BA1", "Book BA2", "Book BA3", "Book BA4"]
    assert [v.status for v in vols] == ["downloaded", "superseded", "superseded", "superseded"]
    assert (vols[0].sha256, vols[0].document_id) == (book["sha"]["BA1"], book["doc"]["BA1"])
    assert from_ba3 == ["Book BA3", "Book BA1", "Book BA2", "Book BA4"]


def test_page_texts_parallel_matches_the_serial_text_pass(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    paths = [str(book["path"][v]) for v in ("BA1", "BA2", "BA3")]
    assert page_texts_parallel(paths, workers=2) == {p: _page_texts(Path(p)) for p in paths}
    assert page_texts_parallel([]) == {}


def test_plan_relocates_locates_keeps_and_counts(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    plan = _plan(pg_dsn)
    assert plan["counts"] == {"rows": 6, "kept": 1, "located": 1, "relocated": 1,
                              "opening_only": 1, "unresolved": 2}
    by_pe = {ch["fact_key"][1]: ch for ch in plan["changes"]}
    assert sorted(by_pe) == ["0605001TST", "0605002TST"]
    n1, n2 = by_pe["0605001TST"], by_pe["0605002TST"]
    assert n1["kind"] == "relocated" and n1["before"]["page_number"] == 1
    assert (n1["after"]["page_number"], n1["after"]["printed_document_sha256"]) == (2, book["sha"]["BA2"])
    assert (n1["after"]["resolution"], n1["after"]["candidate_pages"]) == ("unique", 1)
    assert n2["kind"] == "located" and n2["before"]["page_number"] is None
    assert (n2["after"]["page_number"], n2["after"]["printed_document_sha256"]) == (1, book["sha"]["BA3"])
    assert all(ch["fact_key"][0] == book["sha"]["BA1"] for ch in plan["changes"])
    assert all(set(ch["after"]) == set(RELOCATION_COLUMNS) for ch in plan["changes"])
    assert {s: (v["status"], v["rows"]) for s, v in plan["printed_volumes"].items()} == {
        book["sha"]["BA2"]: ("superseded", 1), book["sha"]["BA3"]: ("superseded", 1)}


def test_plan_reads_only_and_scopes_by_edition(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    with psycopg.connect(pg_dsn) as con:
        before = con.execute(ROW_STATE).fetchall()
    assert _plan(pg_dsn, fiscal_years=[2026])["counts"]["rows"] == 6
    assert _plan(pg_dsn, fiscal_years=[2025])["counts"]["rows"] == 0
    assert _plan(pg_dsn, printed_column=False)["counts"]["located"] == 1
    with psycopg.connect(pg_dsn) as con:
        assert con.execute(ROW_STATE).fetchall() == before


def test_a_relocated_row_is_kept_by_the_next_plan(pg_dsn, tmp_path):
    """The plan is a fixed point: once its rows are written (Task 23c owns the
    transactional write; a plain update stands in here), it plans nothing."""
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        for ch in _plan(pg_dsn)["changes"]:
            cols = list(ch["after"])
            con.execute(f"update provenance_pages set {', '.join(f'{c} = %s' for c in cols)}"
                        " where id = %s", [ch["after"][c] for c in cols] + [ch["id"]])
    again = _plan(pg_dsn)
    assert again["changes"] == []
    assert again["counts"] == {"rows": 6, "kept": 3, "located": 0, "relocated": 0,
                               "opening_only": 1, "unresolved": 2}


def test_new_rows_record_the_printing_volume(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    assert build_narrative_provenance(pg_dsn) == 6
    with psycopg.connect(pg_dsn) as con:
        rows = {pe: (page, res, printed) for pe, page, res, printed in con.execute(
            "select pe_bli, page_number, resolution, printed_document_sha256"
            " from provenance_pages where target_kind = 'narrative'").fetchall()}
    assert rows == {
        "0605001TST": (2, "unique", book["sha"]["BA2"]),
        "0605002TST": (1, "unique", book["sha"]["BA3"]),
        "0605003TST": (None, "unresolved", None),
        "0605004TST": (2, "unique", None),
        "0605005TST": (3, "unique", None),   # opening only: the pre-#195 rule decides
        "0605006TST": (None, "unresolved", None),
    }
    assert build_narrative_provenance(pg_dsn) == 0
    assert _plan(pg_dsn)["changes"] == []
```

- [ ] **Step 6: Run the library tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_narrative_book_set.py -q 2>&1 | tail -3`
Expected: one collection error, `ImportError: cannot import name 'NARRATIVE_CLOSING_SPAN_PAGES' from 'govbudget.jbooks.provenance_pages'`.

- [ ] **Step 7: Implement the book-set relocation**

In `src/govbudget/jbooks/provenance_pages.py`, replace the import block

```python
import re
from decimal import Decimal
from itertools import groupby
from pathlib import Path
```

with

```python
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby
from pathlib import Path
```

Insert this section directly above `def build_narrative_provenance(` (after `find_narrative_page`'s closing `pdf_handle.close()` and its two blank lines):

```python
# ---------------------------------------------------------------------------
# #195 — the volume that PRINTS a narrative (families piece-1 follow-ups,
# design §5.6, Task 23a)
# ---------------------------------------------------------------------------
#
# service_fetch.dedup_service_master_dups keeps one volume per embedded master
# XML and marks the rest superseded; every narrative of the master is attached
# to the kept volume, which prints only its own budget activities. Until #195
# a narrative was searched in that volume alone, by its opening only: 4,157 of
# the 5,601 PB2026 narratives it could not place, and 339 placed ones sat on a
# page that prints the opening but not the paragraph (measured 2026-10-13).
# A narrative is now placed on the first page, in book-set order, that prints
# its opening, its closing within three pages and its PE/BLI anchor.

# BINDING, like NARRATIVE_OPENING_WORDS: the closing-word count shared by the
# relocation below and verify-jbook-narratives (Task 24). Changing it changes
# which stored narrative rows count as printed where they are cited.
NARRATIVE_CLOSING_WORDS = 12
# BINDING: a paragraph may run over a page break, so its closing words may sit
# on the opening's page or on either of the next two.
NARRATIVE_CLOSING_SPAN_PAGES = 3


def narrative_closing(body: str, n_words: int = NARRATIVE_CLOSING_WORDS) -> str:
    """A narrative's closing: its last n_words, whitespace-normalized."""
    return " ".join(body.split()[-n_words:])


def narrative_printed_at(norm_texts: list[str], page_idx: int,
                         opening: str, closing: str) -> bool:
    """True when page page_idx prints the opening and the closing follows on
    that page or the next NARRATIVE_CLOSING_SPAN_PAGES - 1 pages (the window's
    normalized texts joined by one space). BINDING for verify-jbook-narratives'
    paged rule."""
    if not opening or not closing or not 0 <= page_idx < len(norm_texts):
        return False
    if opening not in norm_texts[page_idx]:
        return False
    window = " ".join(norm_texts[page_idx:page_idx + NARRATIVE_CLOSING_SPAN_PAGES])
    return closing in window


def narrative_located_at(norm_texts: list[str], page_idx: int, opening: str,
                         closing: str, anchor: str | None) -> bool:
    """narrative_printed_at, and the opening's page also prints the fact's
    PE/BLI anchor (fact_anchor). The bar for giving a narrative a NEW location:
    an opening and closing alone recur under other program elements (#195's
    033016199ca94aa7 is the case), so a location must also name the program.
    BINDING for verify-jbook-narratives' pageless rule."""
    return (bool(anchor)
            and narrative_printed_at(norm_texts, page_idx, opening, closing)
            and anchor in norm_texts[page_idx])


@dataclass(frozen=True)
class Volume:
    """One PDF of a narrative's book set (#195)."""
    document_id: int
    sha256: str
    file_path: str
    status: str
    title: str


_BOOK_SET_SQL = """
    select o.id, o.sha256, o.file_path, o.status, o.title
    from jbook_documents d
    join jbook_documents o
      on o.fiscal_year = d.fiscal_year and o.org = d.org
     and o.exhibit_family = d.exhibit_family
    where d.id = %s
      and o.sha256 is not null and o.file_path is not null
      and lower(o.file_path) like '%%.pdf'
      and o.status in ('downloaded', 'superseded')
    order by (o.id <> d.id), (o.status <> 'downloaded'), o.title, o.id
"""


def book_set(con, document_id: int) -> list[Volume]:
    """The attached volume first, then every other PDF volume of the same PB
    edition, organization and exhibit family, downloaded before superseded,
    then by title and id.

    Not only the volumes sharing one master-XML sha: two volumes can embed
    regenerated copies of the same master (Army RDT&E Vol 1, docs 344 and 351,
    hold the same 1,189 narratives under masters with different bytes), and
    each prints the other's budget activities.
    """
    return [Volume(*row) for row in con.execute(_BOOK_SET_SQL, (document_id,)).fetchall()]


def _page_texts_job(path: str) -> list[str]:
    return _page_texts(Path(path))


def page_texts_parallel(paths: list[str], *,
                        workers: int | None = None) -> dict[str, list[str]]:
    """pypdf page texts for several PDFs, one worker process per PDF (pypdf is
    pure Python, so processes, not threads). Keyed by the path as given; the
    texts equal _page_texts' for each path."""
    from concurrent.futures import ProcessPoolExecutor

    unique = sorted(set(paths))
    if not unique:
        return {}
    workers = workers or min(8, os.cpu_count() or 1, len(unique))
    if workers <= 1:
        return {p: _page_texts_job(p) for p in unique}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return dict(zip(unique, pool.map(_page_texts_job, unique)))


def resolve_printed_narrative(volumes: list[Volume], texts: dict, plumber_for, *,
                              opening: str, closing: str, pe_bli: str,
                              project_number: str | None,
                              exhibit_family: str | None,
                              words_cache: dict) -> dict | None:
    """The first volume, in book-set order, with a page where the narrative is
    located (narrative_located_at), resolved to that page's first-line bbox.

    texts maps sha256 -> (raw page texts, normalized page texts); plumber_for
    maps sha256 -> an open pdfplumber handle; words_cache is keyed by
    (sha256, page index); pe_bli is the fact anchor. Within a volume the
    existing tie-breaks narrow the located pages (source exhibit, then project
    token) and the honesty vocabulary is unchanged: 'unique' only when one page
    locates it or the tie-breaks narrowed to exactly the page the words
    confirm. candidate_pages is the RAW count of pages in that volume carrying
    the opening, as for every narrative row. Returns None when no volume
    locates the narrative or no word span confirms it.
    """
    for vol in volumes:
        raw, norm = texts[vol.sha256]
        located = [i for i in range(len(norm))
                   if narrative_located_at(norm, i, opening, closing, pe_bli)]
        if not located:
            continue
        preferred = _preferred_candidates(raw, located, project_number=project_number,
                                          exhibit_family=exhibit_family)
        ordered = preferred + [i for i in located if i not in preferred]
        for idx in ordered:
            key = (vol.sha256, idx)
            if key not in words_cache:
                page = plumber_for(vol.sha256).pages[idx]
                words_cache[key] = (page.extract_words(), float(page.width),
                                    float(page.height))
            words, page_width, page_height = words_cache[key]
            span = _find_word_span(words, opening)
            if span:
                uniquely = len(located) == 1 or (
                    len(preferred) == 1 and idx == preferred[0])
                return {
                    "page_number": idx + 1,
                    **_first_line_bbox(words, span),
                    "page_width": page_width, "page_height": page_height,
                    "resolution": "unique" if uniquely else "ambiguous_first",
                    "candidate_pages": sum(1 for t in norm if opening in t),
                    "search_text": opening,
                    "printed_sha256": vol.sha256,
                }
    return None


# The columns a relocation writes, in provenance_pages order. Everything else
# on a narrative row (its identity, amount_text = the searched opening, the
# amount columns) is never written by it.
RELOCATION_COLUMNS = ("page_number", "x0", "x1", "top_pt", "bottom_pt",
                      "page_width", "page_height", "resolution",
                      "candidate_pages", "printed_document_sha256")
_GEOMETRY = ("x0", "x1", "top_pt", "bottom_pt", "page_width", "page_height")

_RELOCATION_ROWS_SQL = """
    select p.id, j.id, j.sha256, n.pe_bli, n.project_number, n.kind,
           n.xml_path, n.body, j.exhibit_family,
           p.page_number, p.x0, p.x1, p.top_pt, p.bottom_pt, p.page_width,
           p.page_height, p.resolution, p.candidate_pages,
           {printed} as printed_document_sha256
    from detail_narratives n
    join jbook_documents j on j.id = n.document_id
    join provenance_pages p
      on p.target_kind = 'narrative' and p.document_sha256 = j.sha256
     and p.pe_bli = n.pe_bli and p.narrative_kind = n.kind
     and p.xml_path = n.xml_path
    where not n.superseded and j.sha256 is not null
      and (%(fy)s::int[] is null or j.fiscal_year = any(%(fy)s::int[]))
    order by p.id
"""


def _stored_location(row) -> dict:
    return dict(zip(RELOCATION_COLUMNS, row[9:19]))


def _as_stored(hit: dict, attached_sha: str) -> dict:
    """A resolve_printed_narrative hit in provenance_pages' column shape."""
    printed = hit["printed_sha256"]
    return {
        "page_number": hit["page_number"], "x0": hit["x0"], "x1": hit["x1"],
        "top_pt": hit["top_pt"], "bottom_pt": hit["bottom_pt"],
        "page_width": hit["page_width"], "page_height": hit["page_height"],
        "resolution": hit["resolution"], "candidate_pages": hit["candidate_pages"],
        "printed_document_sha256": None if printed == attached_sha else printed,
    }


def same_location(a: dict, b: dict) -> bool:
    """Equal relocation columns; the box within 1e-6 pt (numeric vs float)."""
    for col in RELOCATION_COLUMNS:
        x, y = a[col], b[col]
        if col in _GEOMETRY:
            if (x is None) != (y is None) or (
                    x is not None and abs(float(x) - float(y)) > 1e-6):
                return False
        elif x != y:
            return False
    return True


def plan_narrative_relocations(con, *, fiscal_years: list[int] | None = None,
                               texts_for=None, printed_column: bool = True,
                               log=print) -> dict:
    """Which narrative provenance rows are not located where the narrative is
    printed, and where they belong (#195). Reads only.

    Scope: every narrative provenance row of a non-superseded narrative, in
    the given PB editions (all editions when fiscal_years is None).

    A row is KEPT when its stored page prints the narrative
    (narrative_printed_at on the stored volume: printed_document_sha256, or the
    attached document when that is null). Every other row - unresolved, or
    paged where only the opening is printed - is re-resolved across the
    attached document's book set with resolve_printed_narrative. A hit that
    differs from the stored location is a change: 'located' (was pageless) or
    'relocated' (was paged). A paged row with no hit keeps its page and counts
    'opening_only'; an unresolved row with no hit stays 'unresolved'.

    texts_for(paths) -> {path: raw page texts}, default page_texts_parallel.
    printed_column=False reads printed_document_sha256 as null: a read-only
    plan of a database that migration 022 has not reached yet.
    """
    import pdfplumber

    texts_for = texts_for or page_texts_parallel
    sql = _RELOCATION_ROWS_SQL.format(
        printed="p.printed_document_sha256" if printed_column else "null::text")
    rows = con.execute(sql, {"fy": fiscal_years}).fetchall()
    sets: dict[int, list[Volume]] = {}
    for row in rows:
        if row[1] not in sets:
            sets[row[1]] = book_set(con, row[1])
    paths = {v.sha256: v.file_path for vols in sets.values() for v in vols}
    for sha, path in paths.items():
        if not Path(path).exists():
            raise FileNotFoundError(f"document {sha} missing on disk: {path}")
    raw_by_path = texts_for(sorted(paths.values()))
    texts = {sha: (raw_by_path[p], [normalize_ws(t) for t in raw_by_path[p]])
             for sha, p in paths.items()}
    handles: dict[str, object] = {}

    def plumber_for(sha):
        if sha not in handles:
            handles[sha] = pdfplumber.open(paths[sha])
        return handles[sha]

    words_cache: dict = {}
    changes: list[dict] = []
    counts = {"rows": len(rows), "kept": 0, "located": 0, "relocated": 0,
              "opening_only": 0, "unresolved": 0}
    printed: dict[str, dict] = {}
    try:
        for row in rows:
            (pid, doc_id, sha, pe_bli, project_number, kind, xml_path, body,
             exhibit_family) = row[:9]
            stored = _stored_location(row)
            opening, closing = narrative_opening(body), narrative_closing(body)
            stored_sha = stored["printed_document_sha256"] or sha
            paged = (stored["page_number"] is not None
                     and stored["resolution"] in ("unique", "ambiguous_first"))
            if paged and stored_sha in texts and narrative_printed_at(
                    texts[stored_sha][1], stored["page_number"] - 1, opening, closing):
                counts["kept"] += 1
                continue
            hit = resolve_printed_narrative(
                sets[doc_id], texts, plumber_for, opening=opening, closing=closing,
                pe_bli=fact_anchor(pe_bli), project_number=project_number,
                exhibit_family=exhibit_family, words_cache=words_cache)
            if hit is None:
                counts["opening_only" if paged else "unresolved"] += 1
                continue
            after = _as_stored(hit, sha)
            if same_location(stored, after):
                counts["kept"] += 1
                continue
            change_kind = "relocated" if paged else "located"
            counts[change_kind] += 1
            changes.append({"id": pid, "fact_key": [sha, pe_bli, kind, xml_path],
                            "kind": change_kind, "before": stored, "after": after})
            vol = next(v for v in sets[doc_id] if v.sha256 == hit["printed_sha256"])
            entry = printed.setdefault(vol.sha256, {"title": vol.title,
                                                    "status": vol.status, "rows": 0})
            entry["rows"] += 1
    finally:
        for handle in handles.values():
            handle.close()
    scope = "all editions" if fiscal_years is None else f"PB{fiscal_years}"
    log(f"narrative relocation ({scope}): {counts}")
    return {"changes": changes, "counts": counts, "printed_volumes": printed}


```

Replace the whole of `build_narrative_provenance` (from its `def` line to the end of the file):

```python
def build_narrative_provenance(
    dsn: str, *, fiscal_year: int | None = None, keys=None
) -> int:
    """Resolve every non-superseded narrative lacking a narrative provenance row.

    Identity is (document_sha256, pe_bli, narrative_kind, xml_path) — the same
    key fact_id_narrative hashes. Grouped by document (one text pass per PDF;
    per-document word cache since narratives of one book share pages). Returns
    rows actually inserted. Missing document files raise loudly.

    fiscal_year scopes the run to one PB edition's documents (Phase 5G
    per-service backfill — mirrors build_provenance_pages); None keeps the
    historical whole-corpus behavior.

    keys (#29(b), 2026-08-27) narrows to an explicit set of identity tuples
    (document_sha256, pe_bli, narrative_kind, xml_path). The multi-edition
    lineage layer needs a page anchor for a few dozen PB2017–PB2025 narratives
    — the ones a stated edge cites — out of ~18k in those editions; resolving
    all of them costs hours of pdfplumber for pages nothing links to. Scoping
    changes only WHICH rows are attempted, never how one is resolved, so a
    scoped row is identical to the row a whole-edition run would write.
    """
    import pdfplumber

    inserted = 0
    with psycopg.connect(dsn) as con:
        rows = con.execute(
            """
            select j.sha256, j.file_path, n.pe_bli, n.project_number, n.kind,
                   n.xml_path, n.body, j.exhibit_family
            from detail_narratives n
            join jbook_documents j on j.id = n.document_id
            where not n.superseded and j.sha256 is not null
              and (%(fy)s::int is null or j.fiscal_year = %(fy)s)
              and not exists (
                select 1 from provenance_pages p
                where p.target_kind = 'narrative'
                  and p.document_sha256 = j.sha256 and p.pe_bli = n.pe_bli
                  and p.narrative_kind = n.kind and p.xml_path = n.xml_path
              )
            order by j.sha256
            """,
            {"fy": fiscal_year},
        ).fetchall()
        if keys is not None:
            wanted = {tuple(k) for k in keys}
            # row is (sha256, file_path, pe_bli, project_number, kind, xml_path, …)
            rows = [r for r in rows if (r[0], r[2], r[4], r[5]) in wanted]
        for sha, doc_group in groupby(rows, key=lambda r: r[0]):
            narratives = list(doc_group)
            pdf_path = Path(narratives[0][1])
            if not pdf_path.exists():
                raise FileNotFoundError(f"document {sha} missing on disk: {pdf_path}")
            texts = _page_texts(pdf_path)
            norm_texts = [normalize_ws(t) for t in texts]
            words_cache: dict = {}
            pdf_handle = None

            def plumber(path=pdf_path):
                nonlocal pdf_handle
                if pdf_handle is None:
                    pdf_handle = pdfplumber.open(path)
                return pdf_handle

            try:
                for (_, _, pe_bli, project_number, kind, xml_path, body,
                     exhibit_family) in narratives:
                    hit = _resolve_narrative(
                        texts, norm_texts, plumber,
                        snippet=narrative_opening(body),
                        pe_bli=fact_anchor(pe_bli),
                        project_number=project_number,
                        exhibit_family=exhibit_family,
                        words_cache=words_cache,
                    )
                    cur = con.execute(
                        """
                        insert into provenance_pages
                          (target_kind, document_sha256, pe_bli, project_number,
                           narrative_kind, xml_path, amount_text, page_number,
                           x0, x1, top_pt, bottom_pt, page_width, page_height,
                           resolution, candidate_pages)
                        values ('narrative',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        on conflict (document_sha256, pe_bli, narrative_kind,
                                     xml_path)
                          where target_kind = 'narrative' do nothing
                        """,
                        (sha, pe_bli, project_number, kind, xml_path,
                         hit["search_text"], hit["page_number"], hit["x0"],
                         hit["x1"], hit["top_pt"], hit["bottom_pt"],
                         hit["page_width"], hit["page_height"],
                         hit["resolution"], hit["candidate_pages"]),
                    )
                    inserted += cur.rowcount
            finally:
                if pdf_handle is not None:
                    pdf_handle.close()
        con.commit()
    return inserted
```

with:

```python
def build_narrative_provenance(
    dsn: str, *, fiscal_year: int | None = None, keys=None
) -> int:
    """Resolve every non-superseded narrative lacking a narrative provenance row.

    Identity is (document_sha256, pe_bli, narrative_kind, xml_path) — the same
    key fact_id_narrative hashes. Grouped by document; each volume's text is
    extracted once per run (page_texts_parallel) and word boxes are cached per
    (volume, page). Returns rows actually inserted. Missing document files
    raise loudly.

    fiscal_year scopes the run to one PB edition's documents (Phase 5G
    per-service backfill — mirrors build_provenance_pages); None keeps the
    historical whole-corpus behavior.

    keys (#29(b), 2026-08-27) narrows to an explicit set of identity tuples
    (document_sha256, pe_bli, narrative_kind, xml_path). The multi-edition
    lineage layer needs a page anchor for a few dozen PB2017–PB2025 narratives
    — the ones a stated edge cites — out of ~18k in those editions; resolving
    all of them costs hours of pdfplumber for pages nothing links to. Scoping
    changes only WHICH rows are attempted, never how one is resolved, so a
    scoped row is identical to the row a whole-edition run would write.

    #195 (families piece-1 follow-ups, Task 23a): a narrative is located on
    the first page of its document's book set (book_set: the attached volume
    first) where narrative_located_at holds, and printed_document_sha256 names
    that volume when it is not the attached one. Only when no volume locates it
    does the pre-#195 rule decide (its opening alone, in the attached volume),
    so the rows plan_narrative_relocations would write are the rows this
    builder writes.
    """
    import pdfplumber

    inserted = 0
    texts: dict[str, tuple[list[str], list[str]]] = {}
    paths: dict[str, str] = {}
    handles: dict[str, object] = {}

    def plumber_for(sha):
        if sha not in handles:
            handles[sha] = pdfplumber.open(paths[sha])
        return handles[sha]

    with psycopg.connect(dsn) as con:
        rows = con.execute(
            """
            select j.sha256, j.file_path, n.pe_bli, n.project_number, n.kind,
                   n.xml_path, n.body, j.exhibit_family, j.id
            from detail_narratives n
            join jbook_documents j on j.id = n.document_id
            where not n.superseded and j.sha256 is not null
              and (%(fy)s::int is null or j.fiscal_year = %(fy)s)
              and not exists (
                select 1 from provenance_pages p
                where p.target_kind = 'narrative'
                  and p.document_sha256 = j.sha256 and p.pe_bli = n.pe_bli
                  and p.narrative_kind = n.kind and p.xml_path = n.xml_path
              )
            order by j.sha256
            """,
            {"fy": fiscal_year},
        ).fetchall()
        if keys is not None:
            wanted = {tuple(k) for k in keys}
            # row is (sha256, file_path, pe_bli, project_number, kind, xml_path, …)
            rows = [r for r in rows if (r[0], r[2], r[4], r[5]) in wanted]
        try:
            for sha, doc_group in groupby(rows, key=lambda r: r[0]):
                narratives = list(doc_group)
                pdf_path = Path(narratives[0][1])
                if not pdf_path.exists():
                    raise FileNotFoundError(f"document {sha} missing on disk: {pdf_path}")
                volumes = book_set(con, narratives[0][8])
                todo = [v for v in volumes if v.sha256 not in texts]
                for vol in todo:
                    if not Path(vol.file_path).exists():
                        raise FileNotFoundError(
                            f"document {vol.sha256} missing on disk: {vol.file_path}")
                raw_by_path = page_texts_parallel([v.file_path for v in todo])
                for vol in todo:
                    raw = raw_by_path[vol.file_path]
                    texts[vol.sha256] = (raw, [normalize_ws(t) for t in raw])
                    paths[vol.sha256] = vol.file_path
                words_cache: dict = {}      # (sha256, page index) -> words: book set
                attached_words: dict = {}   # page index -> words: the opening-only rule
                for (_, _, pe_bli, project_number, kind, xml_path, body,
                     exhibit_family, _doc_id) in narratives:
                    opening = narrative_opening(body)
                    hit = resolve_printed_narrative(
                        volumes, texts, plumber_for,
                        opening=opening, closing=narrative_closing(body),
                        pe_bli=fact_anchor(pe_bli), project_number=project_number,
                        exhibit_family=exhibit_family, words_cache=words_cache,
                    )
                    if hit is None:
                        hit = _resolve_narrative(
                            texts[sha][0], texts[sha][1], lambda: plumber_for(sha),
                            snippet=opening, pe_bli=fact_anchor(pe_bli),
                            project_number=project_number,
                            exhibit_family=exhibit_family,
                            words_cache=attached_words,
                        )
                    printed = hit.get("printed_sha256")
                    cur = con.execute(
                        """
                        insert into provenance_pages
                          (target_kind, document_sha256, pe_bli, project_number,
                           narrative_kind, xml_path, amount_text, page_number,
                           x0, x1, top_pt, bottom_pt, page_width, page_height,
                           resolution, candidate_pages, printed_document_sha256)
                        values ('narrative',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                %s,%s,%s)
                        on conflict (document_sha256, pe_bli, narrative_kind,
                                     xml_path)
                          where target_kind = 'narrative' do nothing
                        """,
                        (sha, pe_bli, project_number, kind, xml_path,
                         hit["search_text"], hit["page_number"], hit["x0"],
                         hit["x1"], hit["top_pt"], hit["bottom_pt"],
                         hit["page_width"], hit["page_height"],
                         hit["resolution"], hit["candidate_pages"],
                         None if printed in (None, sha) else printed),
                    )
                    inserted += cur.rowcount
        finally:
            for handle in handles.values():
                handle.close()
        con.commit()
    return inserted
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_narrative_book_set.py tests/jbooks/test_migration_022.py tests/jbooks/test_provenance_pages.py tests/jbooks/test_export_site_5f.py -q 2>&1 | tail -2`
Expected: `… passed` with 0 failed — the 9 new library tests, the 6 migration tests, every existing `test_provenance_pages.py` narrative and amount test (their single-volume books print no closing they do not also print, or resolve the same page either way) and the 13 `test_export_site_5f.py` tests (12 at HEAD plus Task 12's; their synthetic book's narrative closing `… $15.750 million supports continued development.` is not printed, so the opening-only rule still decides page 1).

Then the whole suite, since `build_narrative_provenance` is also reached through the CLI: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -2` — expected `… passed` with 0 failed (skips only where a test skips today).

And pyflakes on the touched module, against the HEAD baseline (W1): `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uvx --offline ruff check --isolated --select F,E9 src/govbudget/jbooks/provenance_pages.py tests/jbooks/test_narrative_book_set.py tests/jbooks/narrative_volumes.py tests/jbooks/test_migration_022.py` — expected `All checks passed!` (`provenance_pages.py` has no finding at HEAD; checked 2026-10-13 with the same command).

- [ ] **Step 9: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/provenance_pages.py GovBudget/tests/jbooks/narrative_volumes.py GovBudget/tests/jbooks/test_narrative_book_set.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): locate each narrative in the volume of its book set that prints it (#195)" -m "A narrative is placed on the first page, attached volume first, that prints its opening, its closing within three pages and its PE anchor; printed_document_sha256 names that volume when it is another one. plan_narrative_relocations plans the same rows for the stored ones, read-only." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
