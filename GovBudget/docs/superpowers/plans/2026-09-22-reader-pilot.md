# Reader journey pilot

Roadmap: #89–90. Prepared 2026-09-22. Status: session kit ready; no human sessions. Production page-view reporting and two controlled event deliveries verified September 24; custom-event reporting is unavailable on the current Hobby plan. See [measurement record](2026-09-24-reader-measurement.md).

## Decision and scope

Test whether a reader can reach, check and reuse a defensible budget answer.
Use the existing F-15 family workspace, Virginia exhibit and Cyber Security Research exhibit.
Do not wait for new 3D assets, accounts or a larger dataset to test this journey.
The data is explicitly dated; the pilot does not measure source freshness or validate award attribution.

## Five sessions

Recruit two reporters/researchers, two policy/defense analysts and one interested non-specialist.
Recruitment and external messages have not been sent. Use anonymous participant IDs only.
Allocate 20 minutes per session, with ten minutes for the task and ten for discussion.
Obtain recording consent separately if recording; this kit does not require recordings.

Read the same task without naming buttons:

> A colleague asks what the FY2026 F-15EX procurement figure represents. Find the amount and fiscal status, inspect the supporting evidence, then send a short answer that lets the colleague reopen the same context. Explain whether the figure tells us how much was paid to a contractor.

Start at the homepage with a clean research tray. Do not prompt during the task.
Start the timer at task presentation. Record time to the correct line, first evidence inspection and completed reusable answer.
If the participant is stuck for three minutes, offer help and record assisted completion.
Ask them to explain request versus enacted funding versus payments in their own words.
After the primary task, alternate a Virginia or Cyber topic to see whether the pattern transfers.

Success requires all of: correct F015EX line; FY2026 request and TOA understood;
supporting receipt opened; exact fiscal context and source retained in copied answer;
restored link reproduces the selected record/year; no assertion of contractor payment.
Saving alone is not evidence of comprehension.

## Recording sheet

| ID | Reader type | Device | Seconds to line | Seconds to receipt | Seconds to reuse | Unassisted completion | Correct fiscal status | Restore works | Confusion / help |
|---|---|---|---|---|---|---|---|---|---|
| P01 | Pending | Pending | — | — | — | — | — | — | Not run |
| P02 | Pending | Pending | — | — | — | — | — | — | Not run |
| P03 | Pending | Pending | — | — | — | — | — | — | Not run |
| P04 | Pending | Pending | — | — | — | — | — | — | Not run |
| P05 | Pending | Pending | — | — | — | — | — | — | Not run |

Pilot goal: four of five participants complete unassisted and distinguish fiscal status.
Report every failure and median observed time-to-evidence. This small purposive sample does not estimate population retention.
If failures cluster at a step, fix that step before expanding the experience.

## Measurement contract

Vercel Analytics already supplies page views. New action names:

| Event | Trigger / owner |
|---|---|
| `brief_selected` | User switches F-15 workspace or exhibit topic |
| `funding_selected` | User changes a funding selection |
| `receipt_opened` | Central citation-panel provider, once per open action |
| `official_source_opened` | Explicit official-source link activation |
| `citation_copied` | Successful copy from the citation panel |
| `answer_copied` | Successful Copy answer |
| `view_shared` | Successful selected-view link copy |
| `receipt_saved` | New receipt added to the existing research tray |
| `receipts_exported` | Successful tray citation export |
| `watch_feed_selected` | RSS/Atom link activation |
| `watch_feed_copied` | Successful RSS address copy |

Allowed properties: program, factId, fiscalYear, measure, surface, selection, format, count.
No raw research text, copied prose, saved notes, recipient data or custom user/session identifiers.
Blocked clipboard attempts expose selectable fallback and do not emit copy-success events.
Events are best effort; blocked analytics must not block reader actions.
An official-source event records navigation intent, not proof the external page loaded or was read.
A copied answer is a reuse proxy, not proof it was sent or understood.

The aggregate event counts cannot establish a per-person sequential funnel or retention without session linkage.
Use the observed sessions for answer → receipt → reuse completion; use aggregate action/pageview rates only as directional indicators.
Segment by controlled surface/program and the same publication interval. Do not compare raw counts across unequal traffic windows.

## Baseline and release follow-up

Current human baseline: **not measured**. Current production custom-event baseline: **not collected**.
Automated action verification is implementation evidence, not reader behavior.
After publication, verify custom-event arrival in the configured analytics account, then collect one full week of traffic before interpreting rates.
No recurring automation or external recruitment has been scheduled by this work.
Keep low traffic and blocked analytics visible in the interpretation. Do not infer conversions from local tests.
