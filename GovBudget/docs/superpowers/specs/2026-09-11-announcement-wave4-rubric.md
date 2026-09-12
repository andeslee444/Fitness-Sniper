# Wave 4 — announcement LLM-alias adjudication rubric, written first

**Date:** 2026-09-11 · **Status:** fixed before a single adjudication ran.
**Population:** `data/research/announcements/wave4_queue/chunk_*.json`
(23,824 records, 306 chunks, built by `scripts/mine_announcement_residue.py queue`).
**Precedent:** `docs/superpowers/specs/2026-08-31-lineage-llm-extraction-precision.md` —
the measurement is fixed in advance so it cannot be rewritten around the output.

## 0. What is being claimed

A published link asserts: *this contract action paid for this program element's own work.*
It is published at `high` under method `announcement+lexicon`, it appears in Related Awards
tables on the PE's program page, and its citation card names the defense.gov article, the
archived copy and its sha256. The claim is about ATTRIBUTION, not about whether two strings
resemble each other.

## 1. The three lenses

**Lens P (propose).** Reads one chunk plus that chunk's `lexicon_index` TSV
(`name<TAB>pe_bli<TAB>lexicon_doc<TAB>program_title`, one row per name a PE's own J-book
narrative owns). For each record it may emit at most one proposal per `(piid, pe_bli)`:

```json
{"record_index": 12, "article_id": "2171906", "piid": "W31P4Q20C0023",
 "pe_bli": "8260C53101",
 "program_name": "PAC-3", "lexicon_doc": "345", "match_basis": "llm-alias",
 "announcement_evidence": "Phased Array Tracking Radar to Intercept on Target Advanced Capability-3 missiles",
 "rationale": "PATRIOT is the backronym the announcement spells out; …",
 "verdict": "link"}
```
`verdict` is `link` / `weak` / `wrong` (the wave 1-3 vocabulary). **The default is `wrong`.**
`record_index` and `article_id` are copied from the record the proposal read, and `piid` must
be one of that record's `lake_piids`. Copy `record_index`: a daily digest is one article with
many paragraphs (1,766 of the 23,824 queued records share an article_id with another record in
the same chunk), and the index is what makes the citation quote the paragraph the proposal
actually read. Where `(article_id, piid)` names exactly one record the collector resolves it
without the index; where it names two, it refuses until the index says which.
`program_name`, `pe_bli` and `lexicon_doc` are **copied from one row of the index TSV** —
the same row, verbatim (the name compares case-insensitively, nothing else does). The
collector refuses a proposal that carries no `program_name` or no `lexicon_doc`, and COUNTS a
proposal whose `(program_name, pe_bli, lexicon_doc)` triple is not a row of that org's index
under `invalid_pe_bli`: it does not survive, and no invented code, borrowed code or invented
document id reaches the published "surviving" number. Do not paraphrase the name and do not
carry a name over from another org's index — both read as inventions.
`match_basis` must be one of
`exact-name` · `designator-normalized` · `llm-alias` · `llm-designator-variant` ·
`llm-description` — the collector refuses anything else, and the citation card prints it.
`subaward-description-exact` is NOT available here: the loader treats it as a subaward link.

**Lens A (refute — money and mission).** Given the proposal, the record text and the PE's
lexicon row, tries to break it on: does the award's work belong to THIS line's appropriation
(O&M sustainment attached to an RDT&E or procurement line is the failure mode the 2026-09-04
held-out study found in 3 of 6 refutations), is the named thing a PLATFORM the contract merely
supports rather than the program itself, is the PE a rollup/catch-all.

**Lens B (refute — identity and alternative owner).** Independently tries to break it on: is
the alias real or invented, does a DIFFERENT PE own the same name (the lexicon index is
searchable — name collisions across PEs are common), is the announcement about a different
variant/increment, is the evidence just a contractor name.

Each refute lens returns `{"refuted": true|false, "reason": "<one line>"}`.

## 2. Acceptance rule (binding)

`verdict == "link"` **and** `refute_a.refuted == false` **and** `refute_b.refuted == false`.
Anything else does not survive. A lens that did not run counts as REFUTED and is reported
under `missing_lens` — a half-finished chunk can never read as a clean one.

## 3. Reject by design (each is a refutation, not a judgement call)

- The name is a PLATFORM the contract supports, not the program the PE funds.
- Generic services: engineering support, logistics, base operations, IDIQ ceilings with no
  named program, construction.
- Weak generic names ("STORM", "SHIELD", "Sentinel" used as an English word).
- Catch-all budget lines ("Items Less Than $5 Million", "Ordnance Items <$5M", "Other Support
  Aircraft") — the loader excludes them anyway (`CATCHALL_TITLE`,
  `load_announcement_links.py:103`), so proposing one wastes a refute pass.
- The proposal names no `lexicon_doc` (the collector refuses it, and on a shared BLI code the
  loader could not resolve which member it means).
- `pe_bli` `20`, `30` or `500` — the org-split BLI codes (20 index rows: DHRA 5, DLA 5,
  DTRA 10). `load_announcement_links.py:282` always skips them as `collision`, so a link on one
  can never publish; spend no refute pass on them.

## 4. What this rubric does NOT measure

Precision. The published precision figure on /methodology/ comes from
`scripts/precision_study.py` against `link_precision_samples`, a held-out sample drawn
2026-09-04 and adjudicated separately. **Wave 4 does not re-measure precision, and loading its
links does not change the published figure**: `_link_precision_block` tallies only rows in the
latest `sample_id`, and wave-4 links are not in that sample. If the owner wants the figure to
describe the post-wave-4 corpus, a NEW sample must be drawn
(`uv run python scripts/precision_study.py draw …`) and adjudicated under its own rubric —
that is separate work, separately recorded.

## 5. Output location

One file per chunk at `data/research/announcements/wave4_verdicts/<chunk file name>`:
`{"chunk": "chunk_000_A.json", "proposals": [ … ]}`. Then
`uv run python scripts/mine_announcement_residue.py collect`.

The verdict file is the union of the three lenses for one chunk — lens P writes the proposal
fields, lens A writes `refute_a`, lens B writes `refute_b`, all inside the same proposal
object:

```json
{"chunk": "chunk_000_A.json",
 "proposals": [
   {"record_index": 12, "article_id": "2171906", "piid": "W31P4Q20C0023",
    "pe_bli": "8260C53101",
    "program_name": "PAC-3", "lexicon_doc": "345", "match_basis": "llm-alias",
    "announcement_evidence": "…the announcement's own words…",
    "rationale": "…why lens P believes the award funds THIS line…",
    "verdict": "link",
    "refute_a": {"refuted": false, "reason": "procurement action against a procurement line"},
    "refute_b": {"refuted": false, "reason": "no other PE in the index owns 'PAC-3'"}}
 ]}
```

The file must carry a `proposals` LIST even when the list is empty — a file without one is
counted `malformed_file` and the chunk is recorded as NOT attempted, because a crashed lens
must not read as an adjudicated dry chunk.

Every proposal lens P emits belongs in the file, `weak` and `wrong` included — the verdict
counts are the denominator that makes the surviving count meaningful, and a chunk that
returns only its survivors cannot be told from a chunk nobody read. A `weak`/`wrong` proposal
needs no `refute_a`/`refute_b` (the refute lenses only see `link`s) and no `match_basis`.

## 6. The run protocol (ruling A10, resolved: loop until dry)

The 306 chunks are numbered by DESCENDING announced value — `chunk_000` is the most valuable —
so a partial run always skips the cheapest tail, never an arbitrary slice. Precisely: chunks
are ordered by their TOP record's announced value (the chunk *sums* are not monotonic; 83 of
the 305 adjacent pairs carry a larger sum below a smaller one).
`data/research/announcements/wave4_queue/queue_manifest.json` lists them in exactly that
order, with each chunk's `rank`, record count and `announced_value`; each chunk file repeats
its own `rank` and `announced_value_total`.

- Adjudicate in **rounds of 5 chunks**, in rank order, starting at the highest-ranked chunk
  with no verdict file.
- **Stop after 3 consecutive rounds yield 0 surviving links** — but **the dry counter arms
  only after the first 6 rounds (30 chunks)**. Those rounds are the IDIQ-umbrella band §3
  rejects by design (see the hazard below), so a dry round there says nothing about the tail:
  rounds 1-6 are adjudicated whatever they return, and only from round 7 on can three
  consecutive dry rounds stop the run.
- Or stop at a hard cap of **150 chunks per run**, whichever comes first.
  `wave4_result.json`'s `chunks_attempted` records exactly what ran.
- Dollars are NOT a stopping rule. The distribution is extremely skewed — `chunk_000_A` alone
  carries $235.8B, and while no single chunk exceeds the historically disclosed $278B
  remainder, the top two together ($470.6B) do, because the top announcements are
  multi-billion IDIQ ceilings. Stop by chunk count.
- `collect` accepts a PARTIAL set of verdict files. A chunk with no verdict file is neither
  surviving nor refuted — it was not attempted, and `wave4_result.json`'s `records_attempted`
  and `chunks_attempted` say exactly what ran. Task 25b publishes what was adjudicated, not
  what was queued: a partial run is a smaller true number, not a hole.
- The unadjudicated tail is named in a ROADMAP backlog entry by Task 25b, with its record
  count and chunk count taken from the same two files.

**One hazard the stopping rule has to be read against.** Ranking by announced value puts the
multi-award IDIQ umbrella paragraphs first — `chunk_000_A`'s top record is a $37.4B
198-PIID services award naming no program at all — and §3 rejects exactly those by design. So
the earliest rounds are the ones most likely to return zero survivors *for a reason that says
nothing about the tail*. Read a dry round together with its verdict counts: a round that
proposed nothing is the queue running out of linkable records; a round that proposed and was
refuted is the rubric working. If the first three rounds are dry, record which of the two it
was — and keep going: the counter does not arm until round 7. For scale: the 150-chunk cap covers 11,775 records and $1.478T (92% of
the queued value); a round of 5 chunks is ≈400 records.
