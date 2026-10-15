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
