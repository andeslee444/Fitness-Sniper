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
