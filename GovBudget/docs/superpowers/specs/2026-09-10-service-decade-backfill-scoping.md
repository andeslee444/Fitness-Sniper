# Service J-book decade backfill (PB2017–PB2025) — scoping note

**Date:** 2026-09-10
**Status:** SCOPING ONLY — the GO/NO-GO 5G called for, still not taken
**Filed as:** ROADMAP backlog (the "Service J-book decade backfill" entry)

---

## Context

5G scoped the service justification books to FY2026 and named the rest "a
separate GO/NO-GO after this phase proves the adapter"
(`docs/superpowers/specs/2026-07-03-phase5g-service-jbooks-design.md:76`). The
adapter proved out in two forms:

- **Navy** — live Playwright fetch of the FY index
  (`SERVICE_INDEX_URLS`, `src/govbudget/jbooks/service_fetch.py:44`, currently
  `secnav.navy.mil/fmc/fmb/Documents/26pres/`), because `secnav.navy.mil`
  returns a WAF rejection page to server-side clients.
- **Army / Air Force / Space Force** — the Internet Archive mirror
  (`ARCHIVE_CDX_PREFIX`, `src/govbudget/cli.py:309`, currently
  `asafm.army.mil/Portals/72/Documents/BudgetMaterial/2026*` and
  `saffm.hq.af.mil/Portals/84/documents/FY26*`), because the Army origin is
  Akamai-WAF'd and the Air Force origin is CAC-gated.

No decision followed. `jbook_documents` holds **44 service books (Army 20, Navy
13, Air Force 11), all edition 2026**; editions 2017–2025 have **zero** rows for
orgs A/N/F.

What is *not* missing is the money. The workbook-derived decade series covers
service program elements across all ten editions — `0603502N` has rows in every
`fct_decade_series` edition 2017–2026 — because the R-1/P-1 display workbooks
are service-wide. **What a decade backfill would add is the justification
text**: mission and project narratives, R-2/P-40 detail, and the PDF page
citations that make a narrative quotable. For edition 2026 that text is
substantial — the service books carry **9,222 of the 11,679 FY2026 narratives**
(Army 4,524, Navy 2,437, Air Force 2,261). For 2017–2025 it is zero.

## Options

**A. NO-GO.** Close the entry; state plainly on `/coverage/` and
`/methodology/` that the ten-edition window is defense-wide for justification
text and workbook-only for the services. Cost: hours (copy + a gate assertion
that the sentence matches the data). This is the honest-labelling option and it
closes a live gap: the coverage page says "10 editions loaded — PB2017–PB2026"
without saying the services are one-edition-only.

**B. Partial — PB2024 and PB2025 only.** Two editions × three services ≈ 88
books, the window readers actually compare against FY2026. Cost: days to a
couple of weeks, ~4 GB raw. Every earlier-edition folder name must be verified
first: both fetch paths are pinned to FY2026 strings, so each edition needs its
own confirmed prefix (`.../BudgetMaterial/2025*`, `.../documents/FY25*`,
`.../fmb/Documents/25pres/` are plausible and **unverified**).

**C. Full nine editions (PB2017–PB2025).** ≈ 400 books. The FY2026 service
books alone are ~2.0 GB of the 2.1 GB `data/raw_docs/fy2026` tree (Navy 1.1 GB,
Army 515 MB, AF 358 MB), so nine editions are on the order of **18 GB** of raw
PDF, plus growth in the published R2 store (1.8 GB / 203 PDFs today) for every
book a citation points into. Cost: weeks, dominated by extraction and
provenance-page resolution rather than by download.

## Risks

- **The dedup page-provenance gap multiplies.** Each `(family, master)` group
  keeps one PDF, so facts whose exhibit page lives in a dropped sibling resolve
  `unresolved`. Today that is **8,021 skipped citations**
  (`data/site/manifest.json`), and it is overwhelmingly the service books: Navy
  **10,578 of 14,200** amount provenance rows unresolved, Army 3,255 of 5,523,
  Air Force 733 of 5,313, every defense-wide org **0**. Adding editions at that
  rate adds unresolved citations at that rate. The cross-sibling entry should
  be decided **before or with** this one.
- **Archive coverage for older editions is unverified.** The CDX prefixes were
  confirmed live for FY2026 only
  (`docs/superpowers/reviews/5g-archive/army-book-urls.txt` and
  `af-book-urls.txt`). An edition the Archive never crawled is simply not
  obtainable, and the manual `jbooks ingest-local` drop-dir path needs an
  operator with a browser.
- **Polite scraping and the WAF origins.** Nothing about this work justifies
  hitting a blocked origin harder; the Archive route is the route.
- **Storage and deploy time** grow monotonically, and R2 re-sync is already the
  step whose omission silently degrades every new citation panel.

## The open decision

**A (no-go, label it), B (two editions), or C (nine editions)?**

Recommended order of operations whichever way it goes: decide the cross-sibling
page-resolution entry first, because B and C both scale its defect, and A is
cheap only if the labelling actually ships.
