---
status: diagnosed
phase: 05-snipe-timeline-and-history
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md
started: 2026-02-28T07:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Job Status Timeline on Target Cards
expected: On the /targets page, each target card with an active job shows a horizontal 4-step timeline: Scheduled → Waiting → Attempting → Result. Completed steps show emerald/green fill, the active step pulses blue, and failed steps show red with an AlertCircle icon.
result: pass

### 2. Countdown Timer for Pending Bookings
expected: On the /targets page, targets with a future booking window show a countdown timer like "Booking opens in Xd Xh" or "Xh Xm" that ticks down every second without page refresh.
result: skipped
reason: No targets with future booking windows available to test

### 3. Prominent Failure Messages on Targets
expected: On the /targets page, any target whose last job failed shows a red failure message with an AlertCircle icon and actionable text (not raw error strings). The message is clearly visible, not muted/tiny.
result: skipped
reason: No failed jobs in current data to verify against

### 4. History Page Shows Class Names
expected: On the /history page, each booking entry shows the class name as the primary text (e.g., "Full Body" or "Arms & Abs"). If no class name is available, it falls back to showing the studio name.
result: issue
reported: "Runtime Error: A <Select.Item /> must have a value prop that is not an empty string. Error at SelectItem in src/components/ui/select.tsx (109:5), called from HistoryPage src/app/(dashboard)/history/page.tsx (84:13)"
severity: blocker

### 5. Studio Filter on History Page
expected: The /history page has a studio filter dropdown. Selecting a studio filters the history list to only show bookings for that studio. Changing the filter resets pagination back to the first page.
result: issue
reported: "cannot access history page shows runtime error"
severity: blocker

### 6. Failed Bookings Prominent in History
expected: On the /history page, failed booking entries display a red message with an AlertCircle icon showing a translated/actionable failure reason (not raw error text).
result: issue
reported: "same error - history page inaccessible due to Select.Item runtime error"
severity: blocker

### 7. Per-Studio Success Rates on Dashboard
expected: On the /dashboard page, below the calendar, a section shows per-studio success rates. Each studio displays booked/total counts and a color-coded percentage (green >=80%, yellow 50-79%, red <50%).
result: pass

## Summary

total: 7
passed: 2
issues: 3
pending: 0
skipped: 2

## Gaps

- truth: "History page loads and shows class names as primary text"
  status: fixed
  reason: "User reported: Runtime Error: A <Select.Item /> must have a value prop that is not an empty string"
  severity: blocker
  test: 4
  root_cause: "SelectItem value='' (empty string) rejected by Radix UI Select — changed to value='all' sentinel"
  artifacts:
    - path: "web/src/app/(dashboard)/history/page.tsx"
      issue: "SelectItem value prop was empty string; studioFilter state initialized to '' instead of 'all'"
  missing: []
  debug_session: ""

- truth: "Studio filter dropdown works to filter history by studio"
  status: fixed
  reason: "User reported: cannot access history page shows runtime error"
  severity: blocker
  test: 5
  root_cause: "Same as test 4 — page crash prevented access to filter"
  artifacts:
    - path: "web/src/app/(dashboard)/history/page.tsx"
      issue: "Same root cause as test 4"
  missing: []
  debug_session: ""

- truth: "Failed bookings show prominent red messages in history"
  status: fixed
  reason: "User reported: same error - history page inaccessible"
  severity: blocker
  test: 6
  root_cause: "Same as test 4 — page crash prevented access"
  artifacts:
    - path: "web/src/app/(dashboard)/history/page.tsx"
      issue: "Same root cause as test 4"
  missing: []
  debug_session: ""
