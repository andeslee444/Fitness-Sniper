"""Phase 5B-3 Task 7b: dossier cited-or-absent gate.

Per the plan's evaluator design (dossier_gate bullet):

- all top-50 pe_blis ∈ dim_programs — the pre-batch assertion, also exposed
  standalone via `govbudget dossiers gate --pre` (recon §C: a naive top-50
  over fct_budget_trajectory alone picks service lines without pages).
- a dossier file exists for every top-50 pe_bli and is structurally valid.
- ZERO claims with unresolvable citations: every {"fact_id"} must be a key
  of citations.json; every {"url"} must be the url of a cached snapshot.
- ZERO published claims that contradict their cited fact (ruling
  R-DEC-DOSSIERDRIFT, 2026-09-26; check `claims_agree_with_citations`): a
  stated dollar/HHI figure outside the sentence's own rounding of the
  fact's CURRENT value — any fact kind: a derived recorded_value, a workbook
  cell's amount_thousands, a J-book glyph's amount_text (round 2) — a
  concentration word against the fact's 2023 band, a "top/leading recipient
  family" naming a family other than the one the cited concentration row
  records, a recipient list naming a recipient the PAGE's linked awards
  do not carry (round 2), or a figure given another fiscal year than its
  cited column's (round 3; the column is read from citations.parquet) — the
  same
  govbudget.dossiers.claim_drift.claim_contradictions the exporter withholds
  on. The family and recipient legs need duckdb_path. With none they report
  `family_check` / `recipient_check` False and "not run"; with a path that
  cannot be read the check FAILS with `error` (fail closed, round 2 — an
  unreadable mart is never an empty one).
- >= 80% of claims CORPUS-WIDE carry warehouse (fact_id) citations.
- required sections (what_it_is / why_it_matters / players) are non-empty;
  recent_developments MAY be empty (warehouse-only dossiers are valid).
  TWO EXCEPTIONS, both narrow, both verified against an artifact:
  (1) follow-up to #52, 2026-08 — a tightening, not a loosening: an empty
  required section still fails UNLESS the sidecar's own
  dropped_claims_by_section records that every claim in it was removed for
  failing the evidence standard AND the built page (built_site_dir) actually
  renders the correction note disclosing it. Both conditions are checked
  independently; either one failing still fails the section, exactly as an
  empty required section always has. R-DEC-DOSSIERDRIFT round 2
  (2026-09-26): "disclosing it" means the note's COUNT equals the sidecar's
  dropped_claims and its text is exactly the sentence program-dossier.tsx
  renders for the sidecar's dropped_reasons (expected_correction_note —
  every reason, with its own count), read from the member PAGE
  (/program/{slug}/); a count alone let a note explain 4 of 8 removals.
  (2) 'players' ONLY (Sprint E #67; page-keyed by chain-B fix 2 round 2,
  2026-09-12): an empty players section is honest when the warehouse carries
  nothing THIS PAGE could cite — no award link at this page's identity, no
  lobbying mention the page publishes (a bare-code row on a NON-shared code;
  on a shared code R-INT-9 withholds it from every member — R-DEC-DOSSIER,
  2026-09-26), and no concentration figure that is this member's under
  _concentration_for's test (_has_no_players_evidence).
  Queried live against duckdb_path, never a slug list; with no duckdb_path,
  an unresolvable page identity or a missing mart it is not granted.
- program_categories.csv covers all top-50 pe_blis with an enum category and
  a resolvable source_ref (snapshot:{sha} resolving to a cached snapshot, a
  J-book xml_path, jbook:{pe_bli}:{xml_path}, or lda:{filing_uuid} — the
  conventions documented in govbudget.dossiers.research).

Returns the standard {ok, ...} dict; wired into verify-phase5b3 in Task 9.
"""
from __future__ import annotations

import csv
import html as html_lib
import json
import re
from pathlib import Path

from govbudget.dossiers.batch import (
    ALL_SECTIONS,
    REQUIRED_SECTIONS,
    validate_dossier,
)
from govbudget.dossiers.claim_drift import (
    ClaimDriftIndexError,
    cited_value,
    claim_contradictions,
    concentration_fact_index,
    fact_column_index,
    linked_recipient_index,
    unlinked_recipients,
)

WAREHOUSE_FLOOR = 0.80

CATEGORY_ENUM = frozenset(
    {"drones", "hypersonics", "space", "shipbuilding", "cyber", "default"}
)

_XML_PATH_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9]*\[\d+\](?:/[A-Za-z][A-Za-z0-9]*\[\d+\])*$"
)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _top_pe(top50_list) -> list[str]:
    """Accept top50() tuples or bare pe_bli strings."""
    return [r[0] if isinstance(r, (list, tuple)) else r for r in top50_list]


def _top_pages(top50_list) -> list[tuple[str, str, bool]]:
    """(bare pe_bli, PAGE identity, row carried that identity) per top50() row.

    top50() carries the page slug in element 4 (chain-B fix 3); bare strings
    and the 4-tuples older fixtures pass fall back to the bare pe_bli, which
    is the page for every program that publishes one.

    The third element is the one the caller acts on (ROADMAP #82, 2026-09-12):
    a row that DID name its page has already answered "which member" and a
    missing file for it is missing, full stop. Only a row that named none may
    fall back to guessing from the filenames on disk.
    """
    out: list[tuple[str, str, bool]] = []
    for r in top50_list:
        if isinstance(r, (list, tuple)):
            has_page = len(r) > 4 and bool(r[4])
            out.append((r[0], r[4] if has_page else r[0], has_page))
        else:
            out.append((r, r, False))
    return out


def dim_programs_pe_set(duckdb_path: str | Path) -> set[str]:
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        return {r[0] for r in con.execute("select pe_bli from dim_programs").fetchall()}
    finally:
        con.close()


def pre_batch_check(top50_pe: list[str], dim_programs_pe: set[str]) -> dict:
    """Recon §C assertion: every dossier pe_bli has a program page."""
    pes = _top_pe(top50_pe)
    missing = sorted(set(pes) - set(dim_programs_pe))
    return {"ok": not missing, "count": len(pes), "missing": missing}


_DROPPED_NOTE_RE = re.compile(
    r'<p\b[^>]*\bdata-dossier-dropped-claims="(\d+)"[^>]*>(.*?)</p>', re.DOTALL)

#: MIRROR of site/src/components/program-dossier.tsx's Correction note, word
#: for word (R-DEC-DOSSIERDRIFT round 2): each dropped reason's clause when
#: its count is 1 and otherwise, after the component's subject — "it"/"they"
#: when the reason covers every dropped claim, else "one" or the count.
#: tests/test_dossiers_batch.py::TestCorrectionNoteMirror holds the two
#: together; the order is the component's.
CORRECTION_CLAUSES: dict[str, tuple[str, str]] = {
    # R-DEC-DOSSIERDRIFT round 3: worded for what the exporter checks — the
    # claim's citation does not resolve (a fact_id not in citations.json, a
    # url with no cached snapshot, a malformed citation). It used to say
    # "cited lobbying mentions that did not meet the evidence standard",
    # false on /program/1000/, /program/ATA000/, /program/B02100/ and
    # /program/0603467E/, whose unresolvable drops are J-book narrative and
    # concentration claims.
    "unresolvable_citation": (
        "cited a source the site could not resolve",
        "cited sources the site could not resolve",
    ),
    "stale_value": (
        "stated a figure a later correction changed",
        "stated figures a later correction changed",
    ),
    # R-DEC-DOSSIERDRIFT round 4: "year" added. The fiscal_year sub-reason
    # (round 3) withholds a claim whose figure AGREES with its cite but is
    # given another fiscal year (/program/1203154SF/ what_it_is[3]); "stated
    # a figure or recipient its sources do not support" named neither thing
    # wrong with it.
    "contradicts_citation": (
        "stated a figure, year or recipient its sources do not support",
        "stated figures, years or recipients their sources do not support",
    ),
}
#: the component's clause for dropped claims no reason above accounts for
CORRECTION_OTHER_CLAUSE = "did not meet the evidence standard"



def _page_member(ident, pe_bli: str, page_slug: str):
    """The (account, organization) of the dim_programs row whose PAGE is
    `page_slug`, or None when this page's identity cannot be resolved.

    An ordinary program is its own single member and its slug is the bare
    pe_bli. A split key's member is found by re-deriving each member's slug
    with the exporter's own rule (_ProgramIdentity.slug — the one
    classification shared with both link loaders, ROADMAP #83), never by
    parsing the slug's suffix: the axis that tells a shared code's members
    apart is that rule's answer, not a string convention.
    """
    if not ident.is_split(pe_bli):
        return (None, None) if page_slug == pe_bli else None
    for account, account_title, organization, _has_detail in ident.accounts(pe_bli):
        if ident.slug(pe_bli, account, account_title, organization) == page_slug:
            return (account, organization)
    return None


def _concentration_is_this_members(con, ident, pe_bli, account, organization) -> bool:
    """Mirrors export_site._concentration_for's member test.

    fct_program_concentration aggregates by BARE pe_bli, so on a shared code
    each basis is computed over every member's links on that basis. The
    figure is one member's own exactly when every link on the code is filed
    under that member's key; when more than one key carries links the export
    withholds the whole block from every member page (ROADMAP #82) — even
    where the high basis is one member's, as on 3010 and 3215
    (export_site._concentration_owner) — and it is therefore not this page's
    to cite either. Non-split pe_blis take the bare row unchanged.
    """
    if not con.execute(
        "select count(*) from fct_program_concentration where pe_bli = ?", [pe_bli]
    ).fetchone()[0]:
        return False
    if not ident.is_split(pe_bli):
        return True
    linked = {
        ident.split_key(pe_bli, a, o)
        for a, o in con.execute(
            "select distinct account, organization from fct_budget_to_awards"
            " where pe_bli = ?",
            [pe_bli],
        ).fetchall()
    }
    if len(linked) != 1:
        return False
    return ident.split_key(pe_bli, account, organization) in linked


def _has_no_players_evidence(duckdb_path, pe_bli: str, page_slug: str | None = None) -> bool:
    """True iff the warehouse carries nothing THIS PAGE could cite in 'players'.

    'players' draws on award recipients, lobbying mentions and supplier
    concentration. When all three are empty at this page's identity, an empty
    players section is the honest result, not a generation failure. Queried
    live — never a hardcoded pe_bli list, so a program that later acquires
    awards stops qualifying automatically.

    PAGE-KEYED, not bare-keyed (chain-B fix 2 round 2, 2026-09-12 — the #82
    bare-key/page-key class). A shared BLI code's two members are two pages
    with two different answers, and the bare query answered the union: all 50
    of 3050's crosswalk links sit on the OPN member's account, yet the bare
    count denied the exception to 3050-SCN, whose own page publishes none of
    them and has nothing whatever to name. Each mart is asked the question
    its own key can answer:

      - fct_budget_to_awards carries `account` and `organization`, so a split
        member is asked only about its own links — the same split_key
        export_site._awards_for builds a member's Related Awards table with.
      - fct_program_concentration is keyed by the bare pe_bli, so its figure
        counts as this member's only under _concentration_for's own member
        test (_concentration_is_this_members above).
      - fct_program_lobbying is keyed by the bare pe_bli. RULING
        R-DEC-DOSSIER (controller, 2026-09-26): a bare-code row counts as
        players evidence ONLY for a NON-shared code, where the bare code is
        the page and the exporter publishes the row there. On a shared
        (split) code, ruling R-INT-9 (2026-09-25) withholds every such row
        from every member page — export_site ships `mentions` [] on each
        member (`own_mentions = [] if is_split else …`), because no row
        keyed on a bare code can say which member it describes — so the row
        is not attributable to the member and does not deny the exemption.
        The split test is the exporter's own (`ident.is_split`, i.e.
        `pe_bli in ident.split_pe_blis`), never a separate rule. The mart is
        still queried on every code: a missing lobbying mart is unknown and
        is never granted, shared code or not. A shared-code member with its
        own awards or its own concentration figure still needs players — the
        two checks around this one are unchanged. (Before this ruling every
        bare-code row counted for BOTH members; chain G's #176 rematch put
        one RTX row on bare '3050', and 3050-SCN — nothing of its own to
        cite — was refused the exemption over a row its page cannot show.)

    Anything unknown — no duckdb, a page identity that does not resolve, a
    missing mart, a query error — returns False. The exception must be
    earned, never assumed.
    """
    if duckdb_path is None:
        return False
    page_slug = page_slug or pe_bli
    try:
        import duckdb

        from govbudget.export_site import _fetch_program_identity

        con = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            ident = _fetch_program_identity(con)
            member = _page_member(ident, pe_bli, page_slug)
            if member is None:
                return False
            account, organization = member
            awards_sql = "select count(*) from fct_budget_to_awards where pe_bli = ?"
            params: list = [pe_bli]
            if ident.is_account_split(pe_bli):
                awards_sql += " and account is not distinct from ?"
                params.append(account)
            elif ident.is_org_split(pe_bli):
                awards_sql += " and organization is not distinct from ?"
                params.append(organization)
            if con.execute(awards_sql, params).fetchone()[0]:
                return False
            # Queried on every code (a missing mart raises -> not granted);
            # the answer binds only a NON-shared code (R-DEC-DOSSIER): on a
            # shared code R-INT-9 publishes the bare-code row on no member.
            bare_code_mentions = con.execute(
                "select count(*) from fct_program_lobbying where pe_bli = ?", [pe_bli]
            ).fetchone()[0]
            if bare_code_mentions and not ident.is_split(pe_bli):
                return False
            if _concentration_is_this_members(
                con, ident, pe_bli, account, organization
            ):
                return False
            return True
        finally:
            con.close()
    except Exception:
        # Unknown -> not granted. The exception must be earned, never assumed.
        return False


def expected_correction_note(dropped_claims: int, dropped_reasons: dict | None) -> str | None:
    """The Correction note program-dossier.tsx renders for a sidecar, or
    None when the sidecar names a reason the component has no words for
    (such a drop cannot be shown to be disclosed truthfully).

    dropped_reasons None is a sidecar older than the field: the component
    then states #52's reason for every drop."""
    reasons = (
        {"unresolvable_citation": dropped_claims} if dropped_reasons is None
        else dict(dropped_reasons)
    )
    if any(k not in CORRECTION_CLAUSES for k, n in reasons.items() if n):
        return None
    pronoun = "it" if dropped_claims == 1 else "they"

    def subject(n: int) -> str:
        return pronoun if n == dropped_claims else "one" if n == 1 else str(n)

    parts = []
    for reason, (one, many) in CORRECTION_CLAUSES.items():
        n = reasons.get(reason) or 0
        if n > 0:
            parts.append(f"{subject(n)} {one if n == 1 else many}")
    other = dropped_claims - sum(reasons.get(r) or 0 for r in CORRECTION_CLAUSES)
    if other > 0:
        parts.append(f"{subject(other)} {CORRECTION_OTHER_CLAUSE}")
    return (
        f"{dropped_claims} claim{'' if dropped_claims == 1 else 's'} removed:"
        f" {'; '.join(parts)}."
    )


def _rendered_text(fragment: str) -> str:
    """An HTML fragment's text as a reader sees it: React's <!-- -->
    separators and tags removed, entities decoded, whitespace collapsed."""
    text = re.sub(r"<!--.*?-->", "", fragment, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(html_lib.unescape(text).split())


def _built_page_discloses_drop(
    built_site_dir: Path, page_slug: str, sidecar: dict | None = None,
) -> tuple[bool, str]:
    """(True, "") iff out/program/{page_slug}/index.html renders the
    dropped-claims Correction note (program-dossier.tsx's ScopeNote) and it
    says what the sidecar records — real HTML, not the sidecar's own claim
    that one exists.

    Read on the dossier's PAGE (a split code's member slug, e.g. 3010-SCN;
    the bare /program/3010/ is a stub that never renders a dossier). The
    note's data-dossier-dropped-claims must EQUAL the sidecar's
    dropped_claims and its text must be expected_correction_note's sentence
    for the sidecar's dropped_reasons (R-DEC-DOSSIERDRIFT round 2: a count
    alone let "8 claims removed: 4 cited lobbying mentions …" pass with four
    removals unexplained). (False, why) on a missing file, a read error, a
    present-but-zero or disagreeing count, or any other wording."""
    sidecar = sidecar or {}
    page = Path(built_site_dir) / "program" / page_slug / "index.html"
    if not page.exists():
        return False, f"no built page at program/{page_slug}/index.html"
    try:
        page_html = page.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"built page unreadable ({exc})"
    match = _DROPPED_NOTE_RE.search(page_html)
    if not match or int(match.group(1)) <= 0:
        return False, "the built page renders no Correction note"
    dropped = int(sidecar.get("dropped_claims") or 0)
    if int(match.group(1)) != dropped:
        return False, (f"the note counts {match.group(1)} removed claim(s); the"
                       f" sidecar records {dropped}")
    expected = expected_correction_note(dropped, sidecar.get("dropped_reasons"))
    if expected is None:
        return False, (f"the sidecar's dropped_reasons {sidecar.get('dropped_reasons')}"
                       " name a reason the page has no words for")
    rendered = _rendered_text(match.group(2))
    if rendered != expected:
        return False, f"the note reads {rendered!r}; the sidecar needs {expected!r}"
    return True, ""


def source_ref_resolvable(ref: str, snapshot_shas: set[str]) -> bool:
    """program_categories.csv source_ref conventions (research.py docstring)."""
    ref = (ref or "").strip()
    if not ref:
        return False
    if ref.startswith("snapshot:"):
        return ref.split(":", 1)[1] in snapshot_shas
    if ref.startswith("lda:"):
        return bool(_UUID_RE.fullmatch(ref.split(":", 1)[1]))
    if ref.startswith("jbook:"):
        parts = ref.split(":", 2)
        return (
            len(parts) == 3
            and bool(parts[1])
            and bool(_XML_PATH_RE.fullmatch(parts[2]))
        )
    return bool(_XML_PATH_RE.fullmatch(ref))


def dossier_gate(
    dossier_dir: str | Path,
    citations_path: str | Path,
    snapshots_index: str | Path,
    categories_csv: str | Path,
    top50_list,
    *,
    dim_programs_pe: set[str] | None = None,
    warehouse_floor: float = WAREHOUSE_FLOOR,
    built_site_dir: str | Path | None = None,
    duckdb_path: str | Path | None = None,
    citations_parquet: str | Path | None = None,
) -> dict:
    """The cited-or-absent dossier gate. Returns {ok, checks, totals}.

    citations_parquet (optional): the export's citations.parquet, whose rows
    carry each fact's column (scenario / amount_type) that citations.json
    does not — the fiscal-year leg's input (R-DEC-DOSSIERDRIFT round 3).
    When omitted, the export's own layout is read: citations/citations.parquet
    beside the json/ directory citations.json sits in; when neither exists
    the leg reports `fiscal_year_check` False and "not run". A parquet that
    exists but cannot be read FAILS the check (fail closed).

    built_site_dir (optional, e.g. site/out): when provided, required_sections
    verifies its "empty section, honestly disclosed" exception (see below)
    against the ACTUAL BUILT PAGE, not just the sidecar's own say-so — the
    strongest available proof a reader will see the correction, not just that
    the data claims one exists. Omitted in the standalone `dossiers gate`
    CLI path (run right after `dossiers collect`, before any site build
    exists) — with no build to check, the exception cannot be granted at
    all, and an empty required section fails exactly as it always has.
    """
    dossier_dir = Path(dossier_dir)
    built_site_dir = Path(built_site_dir) if built_site_dir is not None else None
    top_pe = _top_pe(top50_list)
    checks: dict[str, dict] = {}

    # -- pre-batch assertion (also standalone via `dossiers gate --pre`) ----
    if dim_programs_pe is not None:
        checks["pre_batch"] = pre_batch_check(top_pe, dim_programs_pe)

    # -- reference sets -----------------------------------------------------
    citations_path = Path(citations_path)
    citation_rows: dict = (
        _load_json(citations_path) if citations_path.exists() else {}
    )
    fact_ids: set[str] = set(citation_rows.keys())
    # R-DEC-DOSSIERDRIFT: the concentration row behind each concentration
    # fid (family + HHI) and every page's linked-award recipients, read-only
    # from the mart. With no mart (duckdb_path=None) the family and
    # recipient legs cannot run and say so; the figure and band legs need
    # only the citation row and always run. A mart that WAS given but cannot
    # be read fails the check (round 2: fail closed) — never "not run". The
    # fiscal-year leg (round 3) reads each fact's column from citations.parquet
    # (citations.json does not carry it), under the same fail-closed rule.
    drift_error: str | None = None
    recipient_index = None
    if citations_parquet is None:
        beside = citations_path.parent.parent / "citations" / "citations.parquet"
        citations_parquet = beside if beside.exists() else None
    fact_columns: dict = {}
    try:
        concentration_facts = concentration_fact_index(duckdb_path)
        recipient_index = linked_recipient_index(duckdb_path)
        fact_columns = fact_column_index(citations_parquet)
    except ClaimDriftIndexError as exc:
        drift_error = str(exc)
        concentration_facts = {}
    snapshots_index = Path(snapshots_index)
    snapshot_urls: set[str] = set()
    snapshot_shas: set[str] = set()
    if snapshots_index.exists():
        for entry in _load_json(snapshots_index).get("snapshots", []):
            if entry.get("url"):
                snapshot_urls.add(entry["url"])
            if entry.get("sha256"):
                snapshot_shas.add(entry["sha256"])

    # -- walk dossiers --------------------------------------------------------
    missing_files: list[str] = []
    structure_errors: list[str] = []
    unresolved: list[dict] = []
    empty_required: list[str] = []
    undisclosed: list[str] = []
    no_evidence_exempt: list[str] = []
    contradictions: list[dict] = []
    total_claims = 0
    warehouse_claims = 0

    for pe_bli, selected_page, has_page_identity in _top_pages(top50_list):
        # Sprint E (#67): a SPLIT key's sidecar is keyed by its page SLUG
        # ("3010-SCN"), not the bare pe_bli, because E3 gave each
        # (account, pe_bli) pair its own page and the page looks the dossier
        # up by slug. The bare name belongs to the disambiguation stub.
        # chain-B fix 3: the selection itself now carries that page identity,
        # so the gate asks for the page the top-50 actually picked instead of
        # inferring it from the filenames on disk.
        path = dossier_dir / f"{selected_page}.json"
        if not path.exists():
            # Fallback for a caller whose top50_list carries no page identity
            # (bare strings, older 4-tuples): accept exactly one
            # "{pe_bli}-{CODE}.json" sibling; more than one would mean two
            # accounts each claim a dossier for the same key, which is a real
            # defect and must still read as missing.
            #
            # ROADMAP #82 (2026-09-12): guarded on `has_page_identity`. When
            # the selection DID name a member, a lone sibling on disk is the
            # OTHER member's dossier, and accepting it would gate one
            # program's page against the other program's claims — the exact
            # substitution this leg exists to catch, performed by the leg.
            siblings = (
                [] if has_page_identity
                else sorted(dossier_dir.glob(f"{pe_bli}-*.json"))
            )
            if len(siblings) == 1:
                path = siblings[0]
            else:
                # Named by the PAGE the selection asked for, not by the code:
                # "3010" does not say which of two member pages is missing.
                missing_files.append(selected_page)
                continue
        # The dossier's PAGE identity: the file stem, which is the bare
        # pe_bli for an ordinary program and the page SLUG ("3010-SCN") for a
        # split key. Every per-PAGE lookup below keys on this, never on
        # pe_bli, because a shared code's members are distinct pages.
        page_slug = path.stem
        doc = _load_json(path)
        sections = doc.get("dossier", doc) if isinstance(doc, dict) else doc
        errors = validate_dossier(sections)
        if errors:
            structure_errors.extend(f"{pe_bli}: {e}" for e in errors)
            continue
        dropped_by_section = (
            doc.get("dropped_claims_by_section") or {}
            if isinstance(doc, dict)
            else {}
        )
        # R-DEC-DOSSIERDRIFT round 2: the linked-award recipients of THIS
        # PAGE (a split code's member, never the bare code — #82).
        page_recipients = (
            recipient_index.for_page(page_slug) if recipient_index is not None else None
        )
        for section in ALL_SECTIONS:
            claims = sections[section]["claims"]
            if section in REQUIRED_SECTIONS and not claims:
                # TIGHTENING, not a loosening (follow-up to #52, 2026-08):
                # this used to fail EVERY empty required section, with no way
                # to tell "generation never populated this section — a real
                # defect" apart from "every claim in this section was
                # correctly dropped for failing the evidence standard, and
                # the page discloses it." The check now asserts BOTH halves
                # of the honest case explicitly instead of assuming either:
                #   (a) the sidecar itself records that THIS section lost
                #       >=1 claim to the citation-membership filter
                #       (_emit_dossier_sidecars's dropped_claims_by_section —
                #       never hand-set, never keyed to a PE list), AND
                #   (b) the actual BUILT PAGE renders the correction note
                #       explaining it (checked against real HTML, not the
                #       sidecar's own say-so) — only possible when
                #       built_site_dir is supplied.
                # An empty section failing EITHER half still fails, exactly
                # as every empty required section always has; with no build
                # to check (built_site_dir=None), the exception cannot be
                # granted at all and the original, unconditional failure
                # applies. So this check asserts STRICTLY MORE than before,
                # never less.
                section_dropped = dropped_by_section.get(section, 0)
                disclosed = False
                if section_dropped > 0 and built_site_dir is not None:
                    disclosed, why_not = _built_page_discloses_drop(
                        built_site_dir, page_slug,
                        doc if isinstance(doc, dict) else None,
                    )
                    if not disclosed:
                        undisclosed.append(f"{page_slug}: {section}: {why_not}")
                # Sprint E (#67), page-keyed by chain-B fix 2 round 2
                # (2026-09-12): a SECOND legitimate emptiness, distinct from
                # the dropped-claims one above. 'players' can only cite award,
                # lobbying or supplier-concentration data; a page that has
                # NONE of those to cite has no players to name, and writing
                # some would be fabrication — the one thing this project
                # refuses outright.
                #
                # The question is asked at THIS PAGE's identity, not at the
                # bare pe_bli (_has_no_players_evidence). A shared BLI code's
                # two members are two pages: 3050's 50 crosswalk links all
                # carry the OPN member's account, so the bare count denied
                # the exception to 3050-SCN — a page that publishes no award,
                # no lobbying mention and no concentration figure of its own,
                # and therefore has nothing whatever to cite. That bare-key
                # /page-key confusion is the #82 class. Lobbying is the one
                # mart with no member key at all: its bare-code row binds a
                # NON-shared code only (R-DEC-DOSSIER, 2026-09-26), since
                # R-INT-9 renders it on no member of a shared code.
                #
                # This is NOT a loosening: it grants the exception only when
                # the warehouse itself is queried and confirms there is
                # nothing THIS PAGE could cite. A section empty for any other
                # reason still fails exactly as before — including a member
                # that does publish its own links (3010-SCN publishes five),
                # whose empty players section is a real content gap.
                if not disclosed and section == "players":
                    if _has_no_players_evidence(duckdb_path, pe_bli, page_slug):
                        disclosed = True
                        no_evidence_exempt.append(page_slug)
                if not disclosed:
                    # Named by the PAGE (page_slug), like missing_files: on a
                    # shared code "3010: players" does not say which member
                    # page failed.
                    empty_required.append(f"{page_slug}: {section}")
            for i, claim in enumerate(claims):
                total_claims += 1
                citation = claim["citation"]
                if "fact_id" in citation:
                    # TIER NOTE (ROADMAP #80 fix round 1, 2026-09-11). This
                    # check resolves a fact_id; it cannot tell which link tier
                    # the figure behind it rests on. For contractor
                    # concentration that mattered — programs.json carries a
                    # high-confidence-only fid AND an all-links fid, and a page
                    # publishes only the first. The all-links fid is kept out
                    # of reach upstream instead: batch._headline_concentration
                    # projects the block down to the published basis before the
                    # bundle is rendered, so a dossier written after that fix
                    # has no all-links fid to cite. Dossiers generated BEFORE
                    # it may still carry one and resolve cleanly here.
                    warehouse_claims += 1
                    if citation["fact_id"] not in fact_ids:
                        unresolved.append(
                            {
                                "pe_bli": pe_bli,
                                "section": section,
                                "claim": i,
                                "fact_id": citation["fact_id"],
                            }
                        )
                    else:
                        # R-DEC-DOSSIERDRIFT: a PUBLISHED claim whose stated
                        # figure, concentration word or top-family name
                        # contradicts its cited fact's current value, or
                        # whose recipient list names a recipient this page's
                        # linked awards do not carry, fails here — the
                        # exporter should have withheld it
                        # (export_site._emit_dossier_sidecars, same
                        # claim_contradictions). Named by PAGE.
                        fid = citation["fact_id"]
                        row = citation_rows.get(fid)
                        row = row if isinstance(row, dict) else None
                        if row is not None and fid in fact_columns:
                            # the column citations.json leaves out (round 3)
                            row = {**row, **fact_columns[fid]}
                        why = claim_contradictions(
                            claim["text"],
                            row,
                            concentration_facts.get(fid),
                            page_recipients,
                        )
                        if why:
                            contradictions.append({
                                "page": page_slug,
                                "section": section,
                                "claim": i,
                                "fact_id": fid,
                                "kind": (row or {}).get("kind"),
                                "cited_value": cited_value(row),
                                "cited_family": (
                                    concentration_facts.get(fid) or {}
                                ).get("family_key"),
                                "reasons": why,
                                "unlinked_recipients": (
                                    unlinked_recipients(claim["text"], page_recipients)
                                    if "recipient_list" in why else []
                                ),
                                "text": claim["text"],
                            })
                else:
                    if citation["url"] not in snapshot_urls:
                        unresolved.append(
                            {
                                "pe_bli": pe_bli,
                                "section": section,
                                "claim": i,
                                "url": citation["url"],
                            }
                        )

    checks["dossiers_present"] = {
        "ok": not missing_files,
        "expected": len(top_pe),
        "missing": missing_files,
    }
    checks["structure"] = {
        "ok": not structure_errors,
        "errors": structure_errors,
    }
    checks["citations_resolvable"] = {
        "ok": not unresolved,
        "unresolved": unresolved,
    }
    legs_ran = duckdb_path is not None and drift_error is None
    notes: list[str] = []
    if drift_error:
        notes.append(
            f"ERROR — {drift_error}. This check FAILS until the mart reads"
            " (R-DEC-DOSSIERDRIFT round 2: fail closed)"
        )
    elif duckdb_path is None:
        notes.append(
            "top-family and recipient-list legs not run: no mart (duckdb_path)")
    if citations_parquet is None and not drift_error:
        notes.append(
            "fiscal-year leg not run: no citations.parquet (the facts'"
            " scenario / amount_type columns)")
    if contradictions:
        notes.append(
            f"{len(contradictions)} published claim(s) contradict their cited"
            " fact or their page's linked awards (R-DEC-DOSSIERDRIFT —"
            " export-site withholds these): "
            + "; ".join(
                f"{c['page']} {c['section']}[{c['claim']}] cites {c['fact_id']}"
                f" ({c['kind'] or 'unknown kind'}) = {c['cited_value']}"
                + (f", family {c['cited_family']}" if c["cited_family"] else "")
                + f" ({', '.join(c['reasons'])}"
                + (f"; unlinked: {', '.join(c['unlinked_recipients'])}"
                   if c["unlinked_recipients"] else "")
                + f"): {c['text']!r}"
                for c in contradictions
            )
        )
    checks["claims_agree_with_citations"] = {
        "ok": not contradictions and drift_error is None,
        "contradictions": contradictions,
        # a supplied mart that could not be read (the check then fails)
        "error": drift_error,
        # whether the top-family and recipient-list legs ran (they need the
        # mart through duckdb_path); the figure and band legs always run
        "family_check": legs_ran,
        "recipient_check": legs_ran and recipient_index is not None,
        # whether the fiscal-year leg ran (it needs citations.parquet)
        "fiscal_year_check": citations_parquet is not None and drift_error is None,
        "note": " | ".join(notes),
    }
    checks["required_sections"] = {
        "ok": not empty_required,
        "empty": empty_required,
        # R-DEC-DOSSIERDRIFT round 2: why each dropped-empty section's built
        # page did not disclose the drop (count or wording vs the sidecar)
        "undisclosed": undisclosed,
        "no_evidence_exempt": no_evidence_exempt,
        "note": (
            "players exempted on "
            f"{len(no_evidence_exempt)} page(s) (rule of 2026-09-12;"
            " lobbying per R-DEC-DOSSIER, 2026-09-26): no award link at this"
            " page's identity, no lobbying mention this page publishes (a"
            " shared code's bare-code rows are withheld from every member,"
            " R-INT-9), and no concentration figure that is this page's —"
            " nothing to cite: "
            + ", ".join(no_evidence_exempt)
        ) if no_evidence_exempt else "",
    }
    ratio = (warehouse_claims / total_claims) if total_claims else 0.0
    checks["warehouse_ratio"] = {
        "ok": total_claims > 0 and ratio >= warehouse_floor,
        "claims": total_claims,
        "warehouse_cited": warehouse_claims,
        "ratio": ratio,
        "floor": warehouse_floor,
    }

    # -- categories -----------------------------------------------------------
    categories_csv = Path(categories_csv)
    cat_rows: dict[str, dict] = {}
    if categories_csv.exists():
        with categories_csv.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                pe = (row.get("pe_bli") or "").strip()
                if pe:
                    cat_rows[pe] = row
    cat_missing = sorted(set(top_pe) - set(cat_rows))
    cat_bad: list[str] = []
    for pe_bli in top_pe:
        row = cat_rows.get(pe_bli)
        if row is None:
            continue
        if (row.get("category") or "").strip() not in CATEGORY_ENUM:
            cat_bad.append(f"{pe_bli}: category {row.get('category')!r} not in enum")
        if not source_ref_resolvable(row.get("source_ref") or "", snapshot_shas):
            cat_bad.append(
                f"{pe_bli}: unresolvable source_ref {row.get('source_ref')!r}"
            )
    checks["categories"] = {
        "ok": not cat_missing and not cat_bad,
        "missing": cat_missing,
        "errors": cat_bad,
    }

    return {
        "ok": all(c["ok"] for c in checks.values()),
        "checks": checks,
        "totals": {
            "dossiers": len(top_pe) - len(missing_files),
            "claims": total_claims,
            "warehouse_cited": warehouse_claims,
            "warehouse_ratio": ratio,
        },
    }


def print_gate(result: dict) -> None:
    """Human-readable PASS/FAIL rendering for the CLI."""
    for name, check in result["checks"].items():
        status = "PASS" if check["ok"] else "FAIL"
        detail = ""
        if name == "warehouse_ratio":
            detail = (
                f" ({check['warehouse_cited']}/{check['claims']}"
                f" = {check['ratio']:.1%}, floor {check['floor']:.0%})"
            )
        print(f"dossier gate: {name}: {status}{detail}")
        if check.get("note"):
            print(f"  note: {check['note']}")
        if not check["ok"]:
            if check.get("error"):
                print(f"  error: {check['error']}")
            for key in ("missing", "errors", "unresolved", "empty", "undisclosed"):
                for item in check.get(key, [])[:20]:
                    print(f"  {key[:-1] if key.endswith('s') else key}: {item}")
    print(f"dossier gate: {'PASS' if result['ok'] else 'FAIL'}")
