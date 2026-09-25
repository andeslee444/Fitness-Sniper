# Parallel product implementation

Prepared 2026-09-22. Roadmap #166–169. Local implementation; not deployed.

## Product decision

The next product outcome is a reader finding, checking and reusing a defensible
budget answer. The implementation extends the existing investigation journey
and watch feeds while source freshness and attribution remain the trust workstream's
priority. Jev stays an internal editorial aid.

| Track | Delivered locally | Still requires external or human evidence |
|---|---|---|
| #166 Reusable answers | F-15, Virginia and Cyber answers preserve amount, year, status, accounting basis, receipt IDs, source passage and restoring URL. Existing tray and citation controls are reused. | Reader comprehension and production verification. |
| #167 Reader measurement | Controlled action events, success-only clipboard measurement and a five-reader session kit. | Analytics account arrival, a traffic baseline and actual reader sessions. |
| #168 Return visits | Three dated PB2026 comparison briefings, home/search discovery and clearer existing RSS/Atom controls. | Human editorial sign-off and a verified source-refresh-to-feed publication cycle before promising timely updates. |
| #169 Jev review | A frozen 17-claim dossier packet, completed API batch, source-linked review queue and separate assistant review. | Blind human labels, false-approval assessment and measured reviewer time. |

## Important behavior

Answers are deterministic combinations of existing cited records. They do not
invent a cause for a budget change or equate a request with contractor payments.
Missing anchored evidence disables the Virginia/Cyber exhibit answer action;
F-15 can still copy a funding-only answer when a narrative is absent. Clipboard denial reveals
the full selectable answer/address and does not count as a completed copy.

Each dated briefing preserves two independently identified fiscal endpoints.
Cyber's FY2025 endpoint is a total, not enacted funding. F-15 and Virginia name
the P-1/P-40 scope distinction. Frozen value, passage and citation checks stop a
build if the reviewed evidence changes. The cards disclose assistant source
review rather than human sign-off.

Watch controls reuse the existing feed eligibility and RSS/Atom addresses.
Company feeds describe the connection to program records without claiming
supplier revenue. Feed selection measures intent; it does not prove a reader
subscribed or later returned.

Reader events carry controlled identifiers and counts only. No copied prose,
queries, notes or custom person/session identifiers are collected. Aggregate
events cannot establish an individual completion funnel or retention. The
[reader session kit](2026-09-22-reader-pilot.md) supplies the comprehension test.

## Jev outcome

17 of 17 API requests completed and all supplied citation IDs resolved
structurally. Jev flagged nine claims as not established and supported eight.
Separate assistant review upheld the nine flags and questioned three supported
claims, including an actual-TOA amount described as money spent. This is not
human or blinded evaluation and supplies no accuracy or time-saving estimate.

The product decision is to retain a bounded internal review queue, without a
public badge or model-based publication gate. The key remains in the ignored
local environment file and is absent from retained pilot artifacts. Published
claims were not rewritten. See the [frozen pilot report](../../../data/research/jev-editorial/2026-09-22/report.md).

## Verification record

The final implementation passed the complete site unit/component suite:
93 files and 1,366 tests. The Python editorial pilot passed seven tests.
TypeScript, focused lint and design-token checks also passed. Fresh production
builds generated 8,405 static pages, 4,642 searchable pages and 457 feeds.

Browser checks used both desktop and 390px mobile layouts. F-15, Virginia and
Cyber completed native clipboard writes and restored their selected topic,
record and fiscal year. Forced clipboard errors exposed selectable fallback
text. Watch-address copying emitted one successful event; failed copying emitted
none. No horizontal overflow or page errors occurred in the checked flows.
Native clipboard-write promises resolved; direct clipboard reads were denied,
so pasting into another application was not verified.

The production-build preview used canonical fiscalreceipts.com feed URLs and
rendered the local PDF with the highlighted source passage. All three briefing
excerpts were matched against their cited PDF pages. This does not establish
production deployment, analytics arrival or reader understanding.

The F-15 landing page now renders the shared rule's largest eligible FY2026
request, explicitly identified as F015EX, before its navigation. The five other
records remain a separate ledger, including EPAWSS development's missing TOA
figure. Changing the selected aircraft or funding record cannot relabel this
fixed comparison. Its receipt opens the three source inputs totaling
3,014,394 thousand. Both desktop and mobile release screenshots were inspected.

After the final changes, targeted release checks passed for build/page weights,
static markup, accounting basis, first-screen answers, accessibility, typography,
design tokens and motion. The family-lead recomputation leg also passed;
the program-skeleton gate still fails on the separate GAO attributions below.
The full earlier release run also passed search (36/37 cases), performance,
receipt clickthrough, degraded mode, persona journeys and the years matrix.
This is not a claim that the complete release suite passed on the final build.

The final F-15 HTML measures 635,083 raw / 67,875 gzip bytes in the verifier's
runtime, below the unchanged 70,000-byte gzip ceiling. Source objects now share
references in the browser payload; no source fields or receipts were removed.
No gate thresholds have been widened to admit the new features.

## Outstanding release work

The full release suite is not green. These findings must stay visible rather
than being treated as evidence that the product implementation has shipped:

| Gate | Observed failure | Follow-up |
|---|---|---|
| Program skeleton, attribution leg | 70 rendered GAO attributions lack a ratified `y` row in `gao_program_xwalk.csv`. | Reconcile source, adjudication and export in the trust workstream. Do not accept rows from a model verdict. |
| Feed, destination leg | Existing concentration cards link to program pages without a rendered concentration figure, including Virginia. | Reconcile concentration scope and destination rendering under the existing trust/feed work. |
| Flow layout | Two budget-chart labels overlap by approximately 6.1 × 1.1px, before and after a fiscal-year switch. | Repair label placement without changing amounts, node geometry or receipt IDs. |
| Copy | Broad existing navigation, heading, metadata and prose conflicts with the voice gate. | Reconcile authored strings and legitimate source-text exemptions; do not blanket-disable the gate. |

The page-weight audit also caught an outdated agency-page measurement. Its
record was corrected using the verifier's runtime to 195,854 raw / 53,607 gzip
bytes; ceilings remain unchanged. The separate rerun passed. This is a
measurement correction, not extra release headroom.

## Next evidence to collect

1. Resolve the release blockers and rerun the complete suite on a fresh build.
2. After publication, verify event arrival in the configured analytics account.
3. Run the five reader sessions; record understanding and time-to-evidence.
4. Obtain human review of the dated briefings before editorial sign-off.
5. Evaluate Jev on unseen claims with human labels and reviewer time before
   deciding whether its internal use should expand.

No external recruitment, messages, scheduled monitoring or deployment was
performed. DeepSeek delegation was attempted but its provider required Global
regions; the user chose to retain those settings and continue with available
agents.
