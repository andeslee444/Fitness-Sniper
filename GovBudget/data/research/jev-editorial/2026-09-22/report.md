# Jev editorial pilot: one real dossier

Prepared and reviewed 2026-09-22. Roadmap #92.

**Decision: retain a bounded internal review tool. Do not add a public Jev feature or a model publication gate.**
The pilot produces useful citation-support flags, but misses material accounting and scope errors.
Trust repairs and completing the reader journey remain higher product priorities.

## What ran

All 17 remaining claims in the exported Advanced Innovative Technologies dossier (0604250D8Z), without selecting cases by model outcome.
The dossier already records six previously dropped claims; those are outside this batch.
The adapter resolves each cited fact to its exact exported row or narrative and recursively resolves derivation inputs.
It supplies fiscal status, units, accounting basis, workbook locator and source identity when present.
It does not substitute another passage to rescue an incorrectly cited claim.
Locator-only evidence is explicitly distinguished from an exact exported record; this does not mean a PDF was visually reread.

The rubric, claims, evidence and source hashes were frozen before the 17 requests to `jev-1.13.0`.
Only public claim/evidence packets and questions were sent. Credentials remain in the ignored local environment.
No model output edits a dossier, changes attribution, establishes lineage or publishes anything.

## Results

| Check | Result |
|---|---|
| API requests completed | 17/17 |
| Citations structurally resolve | 17/17 |
| Initial local deterministic flags | 3 claims |
| Jev flags | 9 claims, all `not_established` |
| Jev calls supported | 8 claims |
| Separate assistant review | All nine flags upheld; three of eight supported decisions questioned |
| Human labels / false approval rate / false flag rate | Not measured |
| Net human reviewer time saved | Not measured |

Seven flagged mission/project/policy claims cite the same R-1 budget amount, which does not contain the claimed narrative.
One cites only a discretionary component for a combined total.
One asserts PDI details and transitions using only a program-wide amount.
These are failures of support by the exact cited evidence, not proof that every underlying statement is false.

Two clear model misses matter:

- FY2024 actual TOA was described as “actual amounts spent.” Jev approved the wording despite the fiscal fields in its evidence packet.
- A FY2026 request was said to have “rose,” without a comparison endpoint supplied to that independent question.

A third, more interpretive concern describes an all-prior-years aggregate as “drawn” and evidence of sustained scale over time.
The aggregate supports an amount; it does not establish a year-by-year pattern or cash payments.
The assistant supplied proposed corrections/actions in `assistant-review.json`; these are not publication approvals.

## What this establishes

The current structural dossier gate verifies resolvable citations. This sample demonstrates why semantic source-to-claim review adds a different check.
Jev's nine flags offer possible editorial benefit beyond citation existence. The misses show that its supported label cannot replace review.
The local three flags are not a rerun of every warehouse/fiscal validator; no whole-system validator superiority is claimed.
Arithmetic and source identity remain deterministic responsibilities, not model judgments.

This is a fresh real-content batch relative to the earlier development experiment, **not a fresh human-reviewed holdout**.
The separate assistant saw model decisions and had already been told about the accounting error.
It is not blinded ground truth. No accuracy percentage, calibrated threshold or reviewer time-saving claim follows from it.

## Next bounded decision

Keep the queue available to the trust/editorial workstream; do not expand automatically.
For a human pilot, freeze unseen claims before requests, label them before seeing Jev, then alternate baseline and assisted review across matched packets.
Record decision, useful correction, seconds spent, and whether a model flag changed the decision.
Count false approvals among unsupported claims, false flags among supported claims, and abstention/total review volume.
Expand only after net reviewer benefit and acceptable missed-error behavior are observed. Otherwise stop using it for this workflow.

## Artifacts and reproduction

- `cases.json`: frozen complete claims, exact supplied evidence, hashes and initial local checks.
- `manifest.json`: endpoint, model, rubric and batch identity.
- `results.jsonl`: per-request outputs, timing, usage and request hashes.
- `review-queue.md`: claim/evidence pairs with pending human review fields.
- `assistant-review.json` and `assistant-review-notes.md`: separate assistant judgments and proposed corrections.
- `summary.json`: machine-readable raw totals; human evaluation fields deliberately remain null.

From the repository root, `uv run python scripts/review_jev_editorial.py --out <new-directory>` prepares a packet without requests.
Add `--run` for one bounded API batch. Existing results are protected from accidental overwrite.
Use frozen artifacts to reproduce this review; a new preparation uses whatever export is current and can differ.
