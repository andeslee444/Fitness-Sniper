# Production reader measurement — 2026-09-24

## Verified

The authenticated Vercel project reports Web Analytics enabled and existing
data. An account-side query for production page views over the preceding seven
days returned activity, including seven views of `/families/f-15`. These counts
may include the owner and automated verification. They are not an organic-reader
baseline or a comprehension result.

Two actual browser actions on the published F-15E fleet-software FY2026 view
were observed through the browser network panel:

| Action | Event | Transport | Controlled properties |
|---|---|---|---|
| Open budget receipt | `receipt_opened` | POST to `/_vercel/insights/event`, HTTP 200 | program, factId, fiscalYear, measure, surface |
| Copy answer | `answer_copied` | POST to `/_vercel/insights/event`, HTTP 200 | program, factId, fiscalYear, measure, surface |

Both carried program `0207134F`, receipt `44f9ccc1f1518032`, FY2026 and
`request`. The receipt visibly retained the government workbook action,
Exhibit R-1 cell P676, 233,018 USD thousands, and the TOA basis. The transport
check does not prove that the clipboard contents were independently read back.

## Reporting constraint

The authenticated team endpoint reports the active **Hobby** plan.
[Vercel's custom-event documentation](https://vercel.com/docs/analytics/custom-events)
limits custom events to Pro and Enterprise. The account's metric schema exposes
`vercel.analytics_pageview.count`, but no custom-event count metric. A successful
HTTP response therefore establishes delivery, not reportable event retention.
No plan, subscription or account settings were changed.

[The metrics documentation](https://vercel.com/docs/analytics/accessing-metrics-with-vercel-cli)
provides a browser-independent reporting path. Account schema remains the
source of truth: this account uses `analytics_pageview`, rather than the newer
`analytics.page_view` spelling shown in those examples. Browser login is not
needed to establish the current plan limitation.

## Reader pilot

Use the [existing five-reader session kit](2026-09-22-reader-pilot.md) now, with
its observer recording sheet. Record anonymous participant IDs, time to source,
unassisted completion, the retained fiscal context, and understanding that budget
authority is not a contractor payment. Target four of five unassisted completions.

All five sessions remain **not run**. No recruitment messages were sent. The next
human dependency is scheduling participants; more tracking code or a paid plan
is not a prerequisite for those sessions. Keep these controlled verification
clicks out of any claimed organic engagement or reader-success result.
