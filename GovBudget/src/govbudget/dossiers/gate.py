"""Phase 5B-3 Task 7b: dossier cited-or-absent gate.

Per the plan's evaluator design (dossier_gate bullet):

- all top-50 pe_blis ∈ dim_programs — the pre-batch assertion, also exposed
  standalone via `govbudget dossiers gate --pre` (recon §C: a naive top-50
  over fct_budget_trajectory alone picks service lines without pages).
- a dossier file exists for every top-50 pe_bli and is structurally valid.
- ZERO claims with unresolvable citations: every {"fact_id"} must be a key
  of citations.json; every {"url"} must be the url of a cached snapshot.
- >= 80% of claims CORPUS-WIDE carry warehouse (fact_id) citations.
- required sections (what_it_is / why_it_matters / players) are non-empty;
  recent_developments MAY be empty (warehouse-only dossiers are valid).
  EXCEPTION (follow-up to #52, 2026-08 — a tightening, not a loosening):
  an empty required section still fails UNLESS the sidecar's own
  dropped_claims_by_section records that every claim in it was removed for
  failing the evidence standard AND the built page (built_site_dir) actually
  renders the correction note disclosing it. Both conditions are checked
  independently; either one failing still fails the section, exactly as an
  empty required section always has.
- program_categories.csv covers all top-50 pe_blis with an enum category and
  a resolvable source_ref (snapshot:{sha} resolving to a cached snapshot, a
  J-book xml_path, jbook:{pe_bli}:{xml_path}, or lda:{filing_uuid} — the
  conventions documented in govbudget.dossiers.research).

Returns the standard {ok, ...} dict; wired into verify-phase5b3 in Task 9.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from govbudget.dossiers.batch import (
    ALL_SECTIONS,
    REQUIRED_SECTIONS,
    validate_dossier,
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


_DROPPED_CLAIMS_ATTR_RE = re.compile(r'data-dossier-dropped-claims="(\d+)"')



def _has_no_players_evidence(duckdb_path, pe_bli: str) -> bool:
    """True iff the warehouse carries nothing a 'players' claim could cite.

    'players' draws on award recipients, lobbying mentions and supplier
    concentration. When all three are empty for a program, an empty players
    section is the honest result, not a generation failure. Queried live —
    never a hardcoded pe_bli list, so a program that later acquires awards
    stops qualifying automatically.
    """
    if duckdb_path is None:
        return False
    try:
        import duckdb

        con = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            for table in (
                "fct_budget_to_awards",
                "fct_program_lobbying",
                "fct_program_concentration",
            ):
                n = con.execute(
                    f"select count(*) from {table} where pe_bli = ?", [pe_bli]
                ).fetchone()[0]
                if n:
                    return False
            return True
        finally:
            con.close()
    except Exception:
        # Unknown -> not granted. The exception must be earned, never assumed.
        return False


# The exported page sidecar field that says the SITE withholds this page's
# contractor attribution (export_site._concentration_withheld, ROADMAP #82).
# It is a boolean on program_details/{slug}.json's `summary` block, keyed by
# PAGE identity — the same slug the dossier file is named for — because a
# shared code's two members are two pages with two different answers.
_WITHHELD_MARKER = "concentration_withheld"


def _concentration_withheld_on_page(program_details_dir, slug: str) -> bool:
    """True iff the exported sidecar for THIS page carries the shared-code
    withholding marker (chain-B fix 2, 2026-09-12).

    Read from the export, not from a slug list: `_concentration_withheld` is
    recomputed from the warehouse on every export, so a member that stops
    being withheld — its sibling loses its links, the mart row disappears —
    stops qualifying on the next export with no edit here. A page whose
    sidecar is missing, unreadable, malformed or simply says False does not
    qualify; with no program_details_dir supplied at all the exception cannot
    be granted, exactly as _built_page_discloses_drop behaves without a build.
    """
    if program_details_dir is None:
        return False
    path = Path(program_details_dir) / f"{slug}.json"
    if not path.exists():
        return False
    try:
        doc = _load_json(path)
    except (OSError, ValueError):
        return False
    summary = doc.get("summary") if isinstance(doc, dict) else None
    if not isinstance(summary, dict):
        return False
    return summary.get(_WITHHELD_MARKER) is True


def _built_page_discloses_drop(built_site_dir: Path, pe_bli: str) -> bool:
    """True iff out/program/{pe_bli}/index.html actually renders the
    dropped-claims correction note (program-dossier.tsx's ScopeNote,
    data-dossier-dropped-claims > 0) — real HTML, not the sidecar's own
    claim that one exists. False on any missing file, read error, or a
    present-but-zero attribute (would mean the sidecar and the page
    disagree, which is itself something this check must NOT paper over)."""
    page = Path(built_site_dir) / "program" / pe_bli / "index.html"
    if not page.exists():
        return False
    try:
        html = page.read_text(encoding="utf-8")
    except OSError:
        return False
    match = _DROPPED_CLAIMS_ATTR_RE.search(html)
    return bool(match) and int(match.group(1)) > 0


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
    program_details_dir: str | Path | None = None,
) -> dict:
    """The cited-or-absent dossier gate. Returns {ok, checks, totals}.

    built_site_dir (optional, e.g. site/out): when provided, required_sections
    verifies its "empty section, honestly disclosed" exception (see below)
    against the ACTUAL BUILT PAGE, not just the sidecar's own say-so — the
    strongest available proof a reader will see the correction, not just that
    the data claims one exists. Omitted in the standalone `dossiers gate`
    CLI path (run right after `dossiers collect`, before any site build
    exists) — with no build to check, the exception cannot be granted at
    all, and an empty required section fails exactly as it always has.

    program_details_dir (optional, e.g. data/site/json/program_details): the
    exported page sidecars, read ONLY to answer required_sections's
    shared-code withholding exception for `players` (see below). Omitted, as
    built_site_dir is, in the standalone `dossiers gate` CLI path — with no
    export to read, that exception cannot be granted either.
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
    fact_ids: set[str] = (
        set(_load_json(citations_path).keys()) if citations_path.exists() else set()
    )
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
    withheld_exempt: list[str] = []
    total_claims = 0
    warehouse_claims = 0

    for pe_bli in top_pe:
        path = dossier_dir / f"{pe_bli}.json"
        if not path.exists():
            # Sprint E (#67): a SPLIT key's sidecar is keyed by its page SLUG
            # ("3010-SCN"), not the bare pe_bli, because E3 gave each
            # (account, pe_bli) pair its own page and the page looks the
            # dossier up by slug. The bare name belongs to the disambiguation
            # stub. Accept exactly one "{pe_bli}-{CODE}.json" sibling; more
            # than one would mean two accounts each claim a dossier for the
            # same key, which is a real defect and must still read as missing.
            siblings = sorted(dossier_dir.glob(f"{pe_bli}-*.json"))
            if len(siblings) == 1:
                path = siblings[0]
            else:
                missing_files.append(pe_bli)
                continue
        # The dossier's PAGE identity: the file stem, which is the bare
        # pe_bli for an ordinary program and the page SLUG ("3010-SCN") for a
        # split key resolved through the sibling lookup above. Every
        # per-PAGE lookup below keys on this, never on pe_bli, because a
        # shared code's members are distinct pages.
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
                disclosed = (
                    section_dropped > 0
                    and built_site_dir is not None
                    and _built_page_discloses_drop(built_site_dir, pe_bli)
                )
                # Sprint E (#67): a SECOND legitimate emptiness, distinct from
                # the dropped-claims one above. 'players' can only cite award,
                # lobbying or supplier-concentration data; a program that has
                # NONE of those in the warehouse has no players to name, and
                # writing some would be fabrication — the one thing this
                # project refuses outright. Verified on the two lines the key
                # split just added: 3010 (LPD Flight II) and 3050 (Medium
                # Landing Ship) each carry 0 awards, 0 lobbying rows and 0
                # concentration rows, so their generated dossiers correctly
                # produced zero players claims with dropped_claims = 0.
                # This is NOT a loosening: it grants the exception only when
                # the warehouse itself is queried and confirms there is
                # nothing to cite. A section empty for any other reason still
                # fails exactly as before.
                if not disclosed and section == "players":
                    disclosed = _has_no_players_evidence(duckdb_path, pe_bli)
                # chain-B fix 2 (2026-09-12): a THIRD honest emptiness, for
                # 'players' alone. Sprint E's clause above asks the warehouse
                # whether anything EXISTS to cite. This one asks the export
                # whether the site PUBLISHES it: on a shared-code collision
                # member whose union concentration figure describes neither
                # member, `_concentration_withheld` withholds the contractor
                # attribution from the page (ROADMAP #82, rendered as
                # data-who-withheld="shared-code"). A players section there
                # would print on the page precisely the attribution the page
                # declines to make — so empty is the honest state, and the
                # only one consistent with what the reader is shown.
                #
                # Keyed on the MARKER at this dossier's page identity
                # (`page_slug`, the same slug `export_site.slug_index` keys
                # named_primes and lobbied_by by), never on a slug list: the
                # marker is recomputed from the warehouse on every export.
                # Scoped to 'players' because it is the only section whose
                # content is contractor attribution; every other empty
                # required section fails exactly as before.
                if not disclosed and section == "players":
                    if _concentration_withheld_on_page(
                        program_details_dir, page_slug
                    ):
                        disclosed = True
                        withheld_exempt.append(page_slug)
                if not disclosed:
                    empty_required.append(f"{pe_bli}: {section}")
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
    checks["required_sections"] = {
        "ok": not empty_required,
        "empty": empty_required,
        "withheld_exempt": withheld_exempt,
        "note": (
            "players exempted on "
            f"{len(withheld_exempt)} page(s) (2026-09-12): "
            f"{_WITHHELD_MARKER}=true in program_details/{{slug}}.json — the "
            "site withholds this shared code's contractor attribution: "
            + ", ".join(withheld_exempt)
        ) if withheld_exempt else "",
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
            for key in ("missing", "errors", "unresolved", "empty"):
                for item in check.get(key, [])[:20]:
                    print(f"  {key[:-1] if key.endswith('s') else key}: {item}")
    print(f"dossier gate: {'PASS' if result['ok'] else 'FAIL'}")
