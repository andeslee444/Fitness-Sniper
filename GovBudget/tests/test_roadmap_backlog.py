"""The improvement backlog is a ledger, and a ledger has a shape.

Filing a deferral means four things: a number that follows the last one, a
source pointer a reader can open, an effort word from a closed vocabulary,
and a Status line. Before 2026-09-10 the backlog stopped at #88 while sixteen
phase-scale deferrals — seventeen, counting the successor-rails entry Task 4
may already have filed — lived only in spec non-goal lists, plan footnotes, an
ingestion report and live /coverage/ prose. The audit found them by reading
documents, which is a search no gate can repeat.

So this test does not find deferrals. It makes the filed ones stay
well-formed (contiguous numbers, one Status line each, a pointer and an
effort word on the 2026-09-10 cohort), pins the three scoping notes by path
so an entry can never point at a spec nobody wrote, and keeps one subject to
one entry where two tasks could file the same fact. Subjects are asserted by
PHRASE, not by number: sibling tasks append to this same list, so numbers are
assigned at execution time and only the phrase is stable.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "superpowers" / "ROADMAP.md"

SECTION_HEADING = "## Improvement backlog"
ENTRY_RE = re.compile(r"^- \*\*#(\d+)\b")
FIRST_BULLET_NUMBER = 70  # #1-#69 predate the bullet convention (numbered list)

EFFORT_RE = re.compile(r"\bEffort:\s*(hours|days|weeks)\b")
POINTER_RE = re.compile(
    r"\b(?:docs|src|site|dbt|data|migrations|tests|scripts|evals)/[\w./\[\]-]+"
)
STATUS_RE = re.compile(r"\*\*Status:")

# The 2026-09-10 cohort, by subject phrase, in the order the audit's
# ## SWEEPS section lists them. Numbers are deliberately absent.
SUBJECTS = [
    "Service J-book decade backfill",
    "Cross-sibling page resolution for deduped service books",
    "5G visual-judging evidence pack",
    "Outlay-stage flows (Treasury MTS)",
    "California ACFR extraction",
    "Congressional-adds view",
    "Dossier expansion beyond the top 50",
    "PB2015 and PB2016 editions",
    "Pre-2026 narrative paragraph provenance",
    "Accounts / saved searches / alerts",
    "Public text-to-SQL analyst surface",
    "LLM-alias pass residue",
    "Print and reduced-motion captures",
    "Lineage title-only endpoints",
    "Program-genealogy timeline",
    "GAO protest-docket enrichment",
]

# Filed by whichever of Task 4 / Task 24 got there first (task-24 ruling 2).
WSC_SUBJECT = "Key the successors the narratives already state"

# Task 25b files this one only if wave 4 leaves records (task-25.md:1820).
TAIL_SUBJECT = "Announcement LLM-alias pass: residue tail"
RESIDUE_SUBJECT = "LLM-alias pass residue"

SCOPING_NOTES = [
    "docs/superpowers/specs/2026-09-10-accounts-alerts-tier-scoping.md",
    "docs/superpowers/specs/2026-09-10-public-analyst-surface-scoping.md",
    "docs/superpowers/specs/2026-09-10-service-decade-backfill-scoping.md",
]

REQUIRED_NOTE_HEADINGS = ["## Context", "## Options", "## Risks", "## The open decision"]


def backlog_section() -> str:
    text = ROADMAP.read_text(encoding="utf-8")
    start = text.index(SECTION_HEADING)
    nxt = text.find("\n## ", start + 1)
    return text[start : nxt if nxt != -1 else len(text)]


def entries() -> list[tuple[int, str]]:
    """[(number, body)] for every `- **#N ...` bullet in the backlog section."""
    lines = backlog_section().splitlines()
    out, i = [], 0
    while i < len(lines):
        m = ENTRY_RE.match(lines[i])
        if not m:
            i += 1
            continue
        # An entry runs to the next bullet or the next blank line — the prose
        # that follows the list (the 2026-08-24 sweep note) is not an entry,
        # and it mentions `**Status:` a few dozen times.
        j = i + 1
        while j < len(lines) and lines[j].strip() and not ENTRY_RE.match(lines[j]):
            j += 1
        out.append((int(m.group(1)), "\n".join(lines[i:j])))
        i = j
    return out


def test_backlog_numbers_are_contiguous_and_ascending():
    nums = [n for n, _ in entries()]
    assert nums, "no bullet-form backlog entries found"
    assert nums[0] == FIRST_BULLET_NUMBER, f"bullet list starts at #{nums[0]}"
    expected = list(range(nums[0], nums[0] + len(nums)))
    assert nums == expected, f"gap or duplicate: {sorted(set(expected) ^ set(nums))}"


def test_every_entry_carries_exactly_one_status_line():
    for num, body in entries():
        found = STATUS_RE.findall(body)
        assert len(found) == 1, f"#{num} has {len(found)} Status markers, want 1"


@pytest.mark.parametrize("subject", SUBJECTS)
def test_the_2026_09_10_cohort_is_filed(subject):
    hits = [num for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"


def test_the_wsc_successor_rails_entry_is_filed_exactly_once():
    hits = [num for num, body in entries() if WSC_SUBJECT in body]
    assert len(hits) == 1, (
        f"{WSC_SUBJECT!r} filed {len(hits)} times — Task 4 files it, and Task 24"
        " files it only if Task 4 did not"
    )


def test_the_residue_tail_entry_is_cross_referenced_when_it_exists():
    """Task 25b's tail entry and this task's residue entry are one subject."""
    tail = [num for num, body in entries() if TAIL_SUBJECT in body]
    assert len(tail) <= 1, f"{TAIL_SUBJECT!r} filed {len(tail)} times, want at most 1"
    if not tail:
        return
    residue = [body for _, body in entries() if RESIDUE_SUBJECT in body]
    assert len(residue) == 1, f"{RESIDUE_SUBJECT!r} filed {len(residue)} times"
    assert f"#{tail[0]}" in residue[0], (
        f"the residue entry does not cite the measured tail #{tail[0]} — two"
        " ledger entries about one fact"
    )


def test_new_entries_carry_an_effort_word_and_a_source_pointer():
    cohort = [(n, b) for n, b in entries() if "(2026-09-10)" in b]
    assert len(cohort) >= len(SUBJECTS), f"only {len(cohort)} entries dated 2026-09-10"
    for num, body in cohort:
        assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
        assert POINTER_RE.search(body), f"#{num} names no source path"
        assert body.rstrip().endswith(
            "**Status:** open (2026-09-10)."
        ), f"#{num} does not end with the open-status line"


@pytest.mark.parametrize("rel", SCOPING_NOTES)
def test_scoping_notes_exist_and_are_referenced(rel):
    path = ROOT / rel
    assert path.exists(), f"{rel} does not exist"
    body = path.read_text(encoding="utf-8")
    assert len(body) > 1500, f"{rel} is {len(body)} chars — too thin to scope anything"
    for heading in REQUIRED_NOTE_HEADINGS:
        assert heading in body, f"{rel} has no {heading!r} section"
    assert rel in ROADMAP.read_text(encoding="utf-8"), f"no backlog entry cites {rel}"
