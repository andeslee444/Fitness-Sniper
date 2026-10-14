<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21g: Release-1 proof — P3 F-15 history re-pin, and the Python gates and V9 on B@fu-post

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §5.2 "Re-pin" (1. the expected sha computed hermetically from `builder_inputs.json.gz`, the only leaf difference `programs[F015E0].note`; 2. `capture_f15_fixtures.py --expect-sha256 <hermetic sha>` on the B clone; 3. the page snapshot, Task 21h), §7 P3 ("the §5.2 re-pin from B@fu-post (hermetic sha = captured sha), then `test_f15_era_identity`"), §1 "F-15 history" (`f15_funding_history.json` changes only in the F015E0 `note`), Q17 as amended by the owner (the gloss is exactly `[the PB2026 F-15EX AP (F015EX) P-40]`), W3, W5 (the gates that need no deploy), W6 (V9).

**Files:**
- Modify (re-pinned by `scripts/era/capture_f15_fixtures.py`): `tests/fixtures/f15/history.json`, `tests/fixtures/f15/history.sha256`, `tests/fixtures/f15/builder_inputs.json.gz`
- Modify: `tests/fixtures/f15/README.md` — one dated sentence after its first paragraph (anchor on `correction (S5).`, line 5)

**Interfaces:**
Consumes: Task 20's F015E0 note (`src/govbudget/f15_funding_history.py` `PROGRAM_NOTES["F015E0"]["note"]` beginning `This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include`) and its hardened `scripts/era/capture_f15_fixtures.py --site-dir --duckdb --out-dir --expect-sha256` (refuses unless the shipped history's sha256 equals `--expect-sha256`; writes `history.json`, `history.sha256`, `builder_inputs.json.gz` atomically after its checks); `govbudget.f15_funding_history` `_json_bytes`, `build_history`, `build_program_matrix` (as `tests/test_f15_era_identity.py` uses them); Task 11's `verify-era-map` legs a–h; `verify-phase5e`, `verify-lineage`, `verify-phase5b1`; Task 5's `govbudget link-coverage --site-dir DIR --baseline FILE` against `data/research/link_coverage/baseline.json`; Task 21f's exports.
Produces: the re-pinned F-15 fixtures (the pin Task 22c's release-state check and `verify-era-map` leg f read); logs `$L/p3-hermetic.txt`, `p3-capture.json`, `gate-*.log`, `link-coverage-fu-post-B.txt`.

Measured for this task (2026-10-13, read-only): `tests/fixtures/f15/history.sha256` is `c59ccf4f06c73db7fb47b0c505c178fc3e530c9993cf5ef95c311e66eeb2f2ee`, equal to the live export's `json/f15_funding_history.json`; in the pinned history, program `P-1:3010F:AF:F015E0` carries `note` "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft …)" and `note_fact_id` `e7d5bcfb4a30f458`; the golden test rebuilds the history as `build_program_matrix(build_history(source_rows, series, retrieved_at, current_fact_ids)[0], previews, existing_citations=registry, retrieved_at)` over `builder_inputs.json.gz`, and the release export of 2026-10-04 reproduced the pin byte for byte although its `built_at` differed from the fixture's `retrieved_at` (the history bytes do not embed the export's run time).

- [ ] **Step 1: P3.1 — the hermetic history, and the one leaf it moves**

This needs no lake and no `data/site`: the builder runs over the committed fixture with the current code. "Before" is A@fu-pre's history, the deployed one, whatever Task 20 did to the committed pin:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python - "$P/fu-pre-A/site/json/f15_funding_history.json" <<'PY' | tee "$L/p3-hermetic.txt"
import gzip, hashlib, json, sys
from govbudget.f15_funding_history import _json_bytes, build_history, build_program_matrix
inputs = json.loads(gzip.decompress(open("tests/fixtures/f15/builder_inputs.json.gz", "rb").read()))
payload, _, _, _ = build_history(inputs["source_rows"], inputs["series"], retrieved_at=inputs["retrieved_at"],
                                 current_fact_ids=set(inputs["current_fact_ids"]))
out, _, _ = build_program_matrix(payload, inputs["previews"], existing_citations=inputs["registry"],
                                 retrieved_at=inputs["retrieved_at"])
data = _json_bytes(out)
print("hermetic sha256", hashlib.sha256(data).hexdigest())
before, after = json.load(open(sys.argv[1])), json.loads(data)
def diff(a, b, at=()):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in diff(a.get(k), b.get(k), (*at, k))]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, (*at, i))]
    return [] if a == b else [(at, a, b)]
moved = diff(before, after)
print("leaves that moved:", [m[0] for m in moved])
(path, old, new), = moved
program = before[path[0]][path[1]]
GLOSS = "This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include"
assert path[0] == "programs" and path[2] == "note" and program["code"] == "F015E0", path
assert new == old.replace("This exhibit does not include", GLOSS, 1) and new != old
print("the only change: F015E0's note now opens", repr(GLOSS))
PY
```
Expected: `hermetic sha256 d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f` (Task 20a Step 5's preview on the committed fixtures, 139,024 → 139,061 bytes; not `c59ccf4f…`), `leaves that moved: [('programs', 7, 'note')]`, `the only change: F015E0's note now opens 'This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include'`. An assertion error means the history moves anywhere else, or the gloss is not the owner's exact string: stop (design §1: the F-15 history changes only in that note).

- [ ] **Step 2: P3.2 — both B exports ship exactly the hermetic history**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && H=$(awk '/^hermetic sha256/ {print $3}' "$L/p3-hermetic.txt") && : "${H:?run Step 1 first}"
for r in fu-pre-B fu-post-B; do s=$(shasum -a 256 "$P/$r/site/json/f15_funding_history.json" | cut -d' ' -f1); [ "$s" = "$H" ] && echo "$r history = hermetic $H" || echo "$r history $s != hermetic $H"; done
```
Expected: `fu-pre-B history = hermetic <H>` and `fu-post-B history = hermetic <H>` (the Chem Demil write and B7 do not touch the F-15 lines). A mismatch: stop; the lake-built history differs from the code's own rebuild.

- [ ] **Step 3: P3.3 — re-pin the history and the builder inputs from B@fu-post**

The capture refuses unless the shipped history's sha256 equals `--expect-sha256` (piece-1 Task 4; hardened by Task 20 to rebuild from the gzip round-tripped fixture and write its three files atomically after the check):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && H=$(awk '/^hermetic sha256/ {print $3}' "$L/p3-hermetic.txt") && : "${H:?run Step 1 first}"
uv run --project . python scripts/era/capture_f15_fixtures.py --site-dir "$P/fu-post-B/site" --duckdb "$P/fu-post-B/duckdb/govbudget.duckdb" --out-dir tests/fixtures/f15 --expect-sha256 "$H" > "$L/p3-capture.json" 2>&1; echo "capture exit=$?"; cat "$L/p3-capture.json"
test "$(cat tests/fixtures/f15/history.sha256)" = "$H" && echo "pin = hermetic history"
git -C .. diff --stat -- GovBudget/tests/fixtures/f15
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_era_identity.py tests/test_f15_funding_history.py -q 2>&1 | tail -2
```
Expected: `capture exit=0` and the capture's JSON line with `"history_sha256": "<H>"`, `"source_rows": 467`, `"series": 195`, `"previews": 207`, `"current_fact_ids": 20` (the S5 capture's counts; the member lines did not change); `pin = hermetic history`; the diff stat lists `builder_inputs.json.gz` (its `captured_from` names this export), `history.json` and `history.sha256` (Task 20a left the pin for this step); then `… passed` with 0 failed and 0 skipped (the three goldens Task 20a left red are green again). A capture refusal (`capture_f15_fixtures: …`) writes nothing: stop and read its message.

Then record the re-pin in `tests/fixtures/f15/README.md` (G3 notes item 7). Replace:

```markdown
Spec: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` §8 V5,
§9 S0, §6.2, §6.5. Captured once at S0; re-pinned only by the owner-approved F-15
correction (S5).
```
with:

```markdown
Spec: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` §8 V5,
§9 S0, §6.2, §6.5. Captured once at S0; re-pinned only by the owner-approved F-15
correction (S5).
*Re-pinned <YYYY-MM-DD> (piece-1 follow-ups Task 21g, design §5.2) for the
owner-approved F015E0 gloss "[the PB2026 F-15EX AP (F015EX) P-40]" (#206 T9, Q17):
history sha256 d0de9e8b…, captured from the proof export B@fu-post; the page
snapshot moved to schema 2 in Task 21h.*
```

- [ ] **Step 4: W3/W5 on B@fu-post — verify-era-map (a–h), verify-phase5e, verify-lineage, verify-phase5b1**

These read the clone and its scratch database only, so no SAM guard; `verify-phase5b1` alone takes about 4.5 minutes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
for gate in verify-era-map verify-phase5e verify-lineage verify-phase5b1; do (. "$P/fu-post/env.sh" "$P/fu-post-B" && uv run --project . python -m govbudget ${gate}) > "$L/gate-${gate}.log" 2>&1; echo "${gate} exit=$?"; tail -1 "$L/gate-${gate}.log"; done
grep -E "^ *leg [a-h]|^  [a-h][ :]" "$L/gate-verify-era-map.log" | head -12
```
Expected: `verify-era-map exit=0` / `verify-era-map: PASS` with all eight legs passing (b compares `decided_on` with the seed, f the re-pinned F-15 history, g the era minters — including the 0390DOM era rows, whose citations carry `pe_bli` 0390DOM — and h the era book diffs), `verify-phase5e exit=0` / `verify-phase5e: PASS`, `verify-lineage exit=0` / `verify-lineage: PASS`, `verify-phase5b1 exit=0` / `verify-phase5b1: PASS`. A FAIL is a finding on the rehearsed state: stop and explain it.

- [ ] **Step 5: V9 (W6) on B@fu-post — link coverage against the committed baseline**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python -m govbudget link-coverage --site-dir "$P/fu-post-B/site" --baseline data/research/link_coverage/baseline.json > "$L/link-coverage-fu-post-B.txt" 2>&1; echo "exit=$?"; tail -6 "$L/link-coverage-fu-post-B.txt"
```
Expected: `exit=0`; the summary line (budget figures 100.00% source-linked; the PDF-highlighted share), the separate count of detail cards cited by XML path with no fact ID (design Q20, about 440), `link-coverage: compared against data/research/link_coverage/baseline.json …`, `link-coverage: 0 violation(s)`, `link-coverage: PASS` — no figure lost a complete PDF receipt, and the new 0390DOM figures are source-linked.

- [ ] **Step 6: Commit the F-15 re-pin**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/tests/fixtures/f15/history.json GovBudget/tests/fixtures/f15/history.sha256 GovBudget/tests/fixtures/f15/builder_inputs.json.gz GovBudget/tests/fixtures/f15/README.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(f15): re-pin the F-15 history after the F015E0 gloss (#206 T9, Q17) from the follow-ups proof export B@fu-post" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: the commit, `4 files changed` (the three fixtures and the README).
