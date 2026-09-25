# Separate assistant review

All 17 frozen cases were read against the exact evidence supplied to Jev, including recursive financial inputs. This is assistant review, not human sign-off or ground truth. The model labels were visible. The parent had already flagged `why_it_matters:0`, so the review is not blind.

The assistant agreed that the nine model-flagged claims lack complete evidence. Seven cite the same R-1 amount for mission, workforce, partnerships, project descriptions or transfer policy. Another cites only one funding component for a two-component total. The final flagged claim describes a PDI subset and transitions using only the program-wide amount.

Three of eight model-supported claims need revision:

- `0604250D8Z:why_it_matters:0`: the source says FY2024 actual TOA; “actual amounts spent” changes the accounting meaning. The local unresolved-record flag already puts this case in the queue, but Jev itself missed the fiscal error.
- `0604250D8Z:why_it_matters:2`: the FY2026 request amount is supported; “rose” lacks a comparison endpoint in this case. Separate prior questions cannot supply it.
- `0604250D8Z:why_it_matters:7`: the R-2 supports a project-level all-prior-years total. “Drawn” is ambiguous about cash, and the aggregate does not establish sustained annual scale. The local flags do not catch this semantic overreach.

Five model-supported claims are supported by their supplied records. The change claim has both recursive endpoints and the exported percentage, though its public copy should explicitly say FY2026 request versus FY2025 total. The FY2025 total must remain “total,” not “enacted.”

These observations are not an accuracy estimate. The batch covers one real dossier, no human labels are available and net reviewer time is unmeasured. The two straightforward missing-comparison/accounting errors and the more interpretive cumulative-total issue reinforce the decision to keep Jev as an internal queue aid.

## Reviewed briefing examples

All six amount/year/status/basis/edition combinations in `site/src/lib/briefing-specs.json` match current program summary cards. All three narrative excerpts match their specified fact IDs verbatim. The F-15EX scope caveat distinguishes its P-40 passage from the broader P-1 aggregate. Virginia's reconciliation sidecar records different P-1 total and P-40 detail amounts. Cyber retains FY2025 “total” and treats the NKA payoff as planned.

The F-15 selected-view route uses uppercase `variant=EX`, `purpose=buy`, `record=F015EX`, `fy=2026` and `#funding`. No briefing source or narrative amendment was required by this review. Human publication review remains pending.
