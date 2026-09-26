"""Export live Postgres jbook facts to Parquet for the DuckDB mart layer.

Lake provenance invariant (Phase 5E Task 5): every exported budget_lines
row must trace to a source document (source_document_id is not null) — the
same document-join contract the details/detail_narratives exports already
enforce. A provenance-less row can never mint a citation (fact_id_workbook
needs the document sha256) and cannot be independently recomputed by the
verify-phase5e lake gates. Migration 005 made the invariant structural
(source_document_id NOT NULL, deleting the one legacy orphan — id 13541,
a title-NULL duplicate of the PB2026 0601101E fy_2024_actuals row from an
early 5C load); the filter here stays as belt-and-braces.
"""
from pathlib import Path

import duckdb
import psycopg

EXPORTS: dict[str, str] = {
    "budget_lines": (
        "select exhibit, fiscal_year, account, account_title, organization,"
        " budget_activity, budget_activity_title, pe_bli, title, amount_type,"
        " amount_thousands, source_document_id, source_sheet,"
        " coalesce(array_to_string(source_cells, ','), '') as source_cells from budget_lines"
        " where source_document_id is not null"
    ),
    "details": (
        # d.account is the P-40 AppropriationNumber the reconciler already
        # joins budget_lines.account on byte-for-byte. It was not exported,
        # so the detail side of the mart had no way to tell two programs
        # sharing a BLI code apart and summed them (ten PB2026 Navy keys —
        # '3010' is LPD Flight II in 1611N AND Shipboard Tactical
        # Communications in 1810N). NULL for R-1/RDT&E rows, which carry
        # no appropriation on the detail side.
        "select d.pe_bli, d.project_number, d.project_title, d.scenario,"
        " d.amount_millions, d.xml_path, d.reconciled, d.account, j.org,"
        " j.exhibit_family, j.fiscal_year, d.document_id,"
        " j.sha256 as document_sha256"
        " from budget_line_details d join jbook_documents j on j.id=d.document_id"
        " where not d.superseded"
    ),
    "detail_narratives": (
        "select n.pe_bli, n.project_number, n.kind, n.title, n.body, n.xml_path,"
        " j.org, j.fiscal_year, n.document_id"
        " from detail_narratives n join jbook_documents j on j.id=n.document_id"
        " where not n.superseded"
    ),
    "budget_line_awards": (
        # `account` (migration 014, ROADMAP #70) names the ONE program a link
        # belongs to for the pe_bli values two programs share; NULL for every
        # key that names a single program. fct_budget_to_awards joins
        # dim_programs on it so a shared code's two members keep their own
        # awards instead of both showing the union.
        #
        # superseded_* (migration 019, ROADMAP #140): the route an
        # evidence-graded link replaced on its key, recorded by
        # scripts/load_announcement_links.py at the move — or, for the 60
        # moves of 2026-09-19, by migration 020 from the evidence it cites in
        # superseded_evidence. Exported so the move is auditable in the lake.
        #
        # recipient_basis (migration 019; R-DEC-RECIPIENT, R-DEC-DERIVE
        # 2026-09-26): how recipient_name/recipient_uei were decided —
        # 'obligation' / 'announcement_named' / 'uei_tiebreak' from the two
        # loaders' pick, 'pre_rule' on a row they wrote before the rule
        # (019's backfill), NULL on the mechanical crosswalk's account* rows.
        # Appended last, so no earlier column moved.
        "select pe_bli, exhibit, fiscal_year, organization, award_piid,"
        " recipient_name, recipient_uei, matched_obligation, method, confidence,"
        " score, rationale, account, superseded_method, superseded_confidence,"
        " superseded_at, superseded_evidence, recipient_basis"
        " from budget_line_awards"
    ),
    "award_adjudications": (
        # hand-adjudication overlay (migration 010) — the mart coalesces
        # adjudicated_confidence over the mechanical crosswalk confidence
        "select award_piid, pe_bli, adjudicated_confidence, award_verdict,"
        " pair_reason, basis, evidence, refuter_lenses_passed, method,"
        " adjudicated_at from award_pe_adjudications"
    ),
    "announcement_link_reviews": (
        # the announcement path's RECORDED review outcomes (migration 018,
        # ROADMAP #110, decided 2026-09-25; R-DEC-110 2026-09-26): one row per
        # (crosswalk link of a reviewed pair, review record) — wave-4 verdict
        # pairs (reviewer rejections included, adversarial 'not_run'), wave
        # 1-3 survivor-list entries, wave 1-2 refutation-sample entries and
        # (R-DEC-110b) the held-out precision study's refuted attribution
        # verdicts as 'precision_sample' rows (no article; source_file the
        # sample id, entry_index the link_precision_samples id, reason headed
        # by the tier the link was drawn from) —
        # written by scripts/backfill_announcement_link_reviews.py. The mart
        # (source jbook_announcement_link_reviews) grades a high announcement
        # link on them. Every column but the table's own recorded_at (a run
        # timestamp, which would make the file differ run to run), ordered by
        # the table's key so the file is byte-stable over the same table.
        "select award_piid, pe_bli, exhibit, fiscal_year, record_kind,"
        " reviewer_verdict, adversarial_verdict, adversarial_lenses_passed,"
        " upholds, article_id, article_source, record_index, entry_index,"
        " cites_reviewed_article, reason, reviewed_at, source_file"
        " from announcement_link_reviews"
        " order by award_piid, pe_bli, exhibit, fiscal_year, source_file,"
        " record_kind, entry_index"
    ),
    "documents": (
        # rel_path relativizes the machine-specific absolute file_path
        "select id, org, exhibit_family, fiscal_year, title, source_url, sha256,"
        " bytes, downloaded_at,"
        " 'fy' || fiscal_year || '/' || lower(org) || '/' || title as rel_path"
        " from jbook_documents where status = 'downloaded' and sha256 is not null"
    ),
    "program_lineage": (
        "select from_pe_bli, to_pe_bli, fiscal_year, relation, portion_amount,"
        " confidence, evidence_fact_id, evidence_sentence, evidence_page, inference_basis"
        " from program_lineage"
    ),
    "program_family": "select pe_bli, family_id from program_family",
}


#: The methods scripts/load_announcement_links.py owns (its OWNED_METHODS,
#: derive_ap_links.EVIDENCE_GRADED_METHODS): it deletes and re-inserts every
#: row carrying one of them on each run, so the newest created_at among them
#: is the loader's last run.
LOADER_METHODS = ("announcement+lexicon", "subaward+lexicon")

#: The chain order the check below enforces (R-DEC-LOADER, 2026-09-26).
CHAIN_ORDER = ("migrate -> scripts/load_announcement_links.py ->"
               " scripts/backfill_announcement_link_reviews.py ->"
               " jbooks export-facts -> build (dbt)")


class ChainOrderError(RuntimeError):
    """export-facts was reached out of CHAIN_ORDER; nothing was written."""


def check_reviews_follow_loader(pg) -> None:
    """Refuse to export when announcement_link_reviews was not backfilled
    AFTER the link loader's last run (R-DEC-LOADER).

    The mart grades every announcement link on the review rows (#110): a table
    written before the loader's last rebuild misses the links that rebuild
    added and carries cites_reviewed_article against source rows it replaced,
    and an empty table beside loaded links would publish every announcement
    link as unreviewed. The loader's last run is the newest created_at among
    the rows it owns (it deletes and re-inserts them all); the backfill's is
    its rows' recorded_at (one transaction). With no loader rows there is
    nothing to grade and nothing to check.

    The same holds for the held-out precision study (R-DEC-110b): the
    backfill copies its refuted attribution verdicts in as precision_sample
    rows, so a refutation adjudicated after the backfill's run is refused
    too."""
    last_load = pg.execute(
        "select max(created_at) from budget_line_awards where method = any(%s)",
        (list(LOADER_METHODS),),
    ).fetchone()[0]
    if last_load is None:
        return
    n_reviews, first_recorded = pg.execute(
        "select count(*), min(recorded_at) from announcement_link_reviews"
    ).fetchone()
    if n_reviews == 0:
        raise ChainOrderError(
            f"no announcement_link_reviews row, but the link loader last ran"
            f" {last_load:%Y-%m-%d %H:%M:%S%z}: run"
            f" scripts/backfill_announcement_link_reviews.py first — nothing"
            f" exported (chain order: {CHAIN_ORDER})")
    if first_recorded < last_load:
        raise ChainOrderError(
            f"announcement_link_reviews was recorded"
            f" {first_recorded:%Y-%m-%d %H:%M:%S%z}, before the link loader's"
            f" last run ({last_load:%Y-%m-%d %H:%M:%S%z}): re-run"
            f" scripts/backfill_announcement_link_reviews.py — nothing exported"
            f" (chain order: {CHAIN_ORDER})")
    # R-DEC-110b: the held-out precision study's refuted attribution verdicts
    # are review records too (precision_sample rows). One judged after the
    # backfill ran is a refutation the table does not carry, and the mart
    # would keep that known-refuted link at high.
    last_refutation = pg.execute(
        "select max(adjudicated_at) from link_precision_samples"
        " where verdict = 'refuted' and rubric = 'attribution'"
    ).fetchone()[0]
    if last_refutation is not None and first_recorded < last_refutation:
        raise ChainOrderError(
            f"announcement_link_reviews was recorded"
            f" {first_recorded:%Y-%m-%d %H:%M:%S%z}, before the precision"
            f" study's last refuted attribution verdict"
            f" ({last_refutation:%Y-%m-%d %H:%M:%S%z}): re-run"
            f" scripts/backfill_announcement_link_reviews.py — nothing exported"
            f" (chain order: {CHAIN_ORDER})")


def export_facts(dsn: str, *, parquet_dir: Path) -> list[Path]:
    # R-DEC-LOADER: checked before the output directory exists, so a refusal
    # leaves no partial export behind.
    with psycopg.connect(dsn) as pg:
        pg.read_only = True
        check_reviews_follow_loader(pg)
    out_dir = parquet_dir / "jbooks"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    con = duckdb.connect()
    try:
        with psycopg.connect(dsn) as pg:
            for name, sql in EXPORTS.items():
                cur = pg.execute(sql)
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
                out = out_dir / f"{name}.parquet"
                con.execute("drop table if exists _t")
                col_defs = ", ".join(f'"{c}" varchar' for c in cols)
                con.execute(f"create table _t ({col_defs})")
                if rows:
                    con.executemany(
                        f"insert into _t values ({', '.join(['?'] * len(cols))})",
                        [[None if v is None else str(v) for v in row] for row in rows],
                    )
                out_sql = str(out).replace("'", "''")
                con.execute(f"copy _t to '{out_sql}' (format parquet, compression zstd)")
                written.append(out)
    finally:
        con.close()
    return sorted(written)
