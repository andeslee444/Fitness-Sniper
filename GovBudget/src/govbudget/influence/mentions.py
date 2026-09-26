"""Deterministic program-mention extractor for LDA lobbying activity descriptions.

Strategy (LLM-free, citation-ready):
  For each program in dim_programs, generate candidate match terms, each
  tagged with a KIND:
    - "pe_code"     — the pe_bli code itself (exact, case-insensitive). An
                       ALL-DIGIT code ("2025", "14") counts only where a
                       budget-line label names it ("BLI 2025", "P-1 line
                       14") — ROADMAP #176; see _build_code_re.
    - "alias"       — a curated alias from dbt/seeds/program_aliases.csv
                       (only for pe_blis present in the supplied programs set).
    - "title_token" — a title word ≥5 chars that is non-generic (see
                       GENERIC_WORDS) and is NOT already a curated alias for
                       this program (an alias-worthy word is tagged "alias"
                       even where it also happens to be a title token — the
                       curation is the stronger signal).

  Each term is matched against activity description text using a
  word-boundary regex (case-insensitive).

Evidence rule (#52 fix — see docs/superpowers/ROADMAP.md item 52):
  A single common title word appearing in a filing's activity description is
  NOT evidence that the filing names the program. Four independent reviewers
  found the previous one-token threshold producing rows like "Ground Based
  Midcourse (MD08) matched: Based" and "CYBERCOM Activities matched:
  Activities" (the latter via an unrelated company, BP AMERICA). No stoplist
  closes this — the fix is an evidence-tier threshold, not a bigger blocklist
  (GENERIC_WORDS is retained as a precision aid, not the sole defence).

  For a given (filing_uuid, pe_bli) pair, ALL matching terms are collected
  across every LDA activity row belonging to that filing (lda_activities is
  grained on (filing_uuid, issue_code); the mention row is grained on the
  filing, not one activity line) before a decision is made. A row is emitted
  ONLY when one of the following holds, in this priority order:
    1. evidence_kind="pe_literal"   — the exact pe_bli code appears (an
                                       all-digit code only as a named
                                       budget line, #176).
    2. evidence_kind="alias"        — a curated, human-verified alias appears
                                       (single-word aliases are trusted alone
                                       because a person confirmed the mapping,
                                       unlike an arbitrary title word).
    3. evidence_kind="multi_token"  — >=2 DISTINCT non-generic title tokens
                                       appear. matched_term is those tokens
                                       joined by "|" in title order (e.g.
                                       "Ground|Midcourse") — this is the
                                       legible, auditable record of exactly
                                       which words co-occurred; a reader does
                                       not have to guess what "evidence" means.
  A single distinctive title token (e.g. "Midcourse" alone) still does NOT
  qualify — the rule is evidence, not rarity (see
  tests/influence/test_mentions_evidence.py::
  test_one_distinctive_token_still_does_not_qualify).

  Priority order (pe_literal > alias > multi_token) is this implementation's
  choice where more than one tier qualifies simultaneously; the task spec
  left it unordered. pe_literal is an exact code match (least ambiguous);
  alias is human-curated; multi_token is the weakest of the three qualifying
  tiers, so it only wins when nothing stronger is present.

Shared codes (RULING R-DEC-176b, 2026-09-26):
  13 codes carry two or three dim_programs rows (two programs filed under one
  bare pe_bli, e.g. 1350 "Infantry Weapons Ammunition" and "Missile
  Industrial Facilities"). A mention row is keyed on the bare code, so a
  shared code is matched against EVERY member's title, each title on its
  own: a multi_token row needs >=2 distinct words from ONE member's title (a
  pair split across two members' titles names neither program), matched_term
  records the words of every member title that qualified (titles in sorted
  order, each title's words in title order), and the row is the CODE's —
  it never names a member. RULING R-INT-9 withholds every shared-code row
  from every member's program page; /filing/ labels it with both members'
  names beside the shared-code note. Before this ruling the code kept only
  the LAST member row's title, so the rows depended on the order the caller
  passed dim_programs in — the stage-1 check measured 12,509 and 12,487 rows
  on two as-is runs of the same corpus, 12,571 sorted and 12,432 reversed.
  The terms now do not depend on input order at all.

  Every match row carries: filing_uuid, pe_bli, matched_term, evidence_kind,
  description_snippet.

Honesty conventions:
  - Column names contain no causal language ('caused', 'because', 'won_due').
  - Presence of a mention indicates a statutory disclosure; no inference
    of causation or influence is made here or in the SQL marts.
  - The claim rendered on the site is "keyword co-occurrence", never
    "named" — a single common word is not a naming (see #52).
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Sequence

# Words too generic to be meaningful single-token program identifiers.
# ACQUISITION, ACTIVITIES, BASED, CHEMICAL, EQUIPMENT, SERVICES, ARMED,
# STRIKE, FOREIGN added 2026-08 (#52) — the review found each of these
# slipping through the original 60-word list and producing a false-naming
# row (e.g. "Based" from "Ground Based Midcourse", "Services" from "Federal
# Investigative Services IT" — the list had only the singular SERVICE).
GENERIC_WORDS = {
    "ACQUISITION", "ACTIVITIES", "ADVANCED", "ANALYSIS", "ARMED", "BASED",
    "BASIC", "CAPABILITIES", "CENTER", "CHEMICAL", "COMMAND", "COMMON",
    "CONTROL", "CYBER", "DEFENSE", "DEPARTMENT", "DEVELOPMENT", "DOMAIN",
    "ENTERPRISE", "EQUIPMENT", "EVALUATION", "FEDERAL", "FOREIGN", "FUTURE",
    "GLOBAL", "HIGH", "INFORMATION", "INNOVATION", "INTEGRATION",
    "EDUCATION", "INTELLIGENCE", "INTERNATIONAL", "JOINT", "LONG",
    "MANAGEMENT", "MISSION", "NATIONAL", "NETWORK", "NUCLEAR", "OFFICE",
    "OPERATIONAL", "OPERATIONS", "OTHER", "POLICY", "PRODUCTION", "PROGRAM",
    "PROGRAMS", "RAPID", "RANGE", "RESEARCH", "SCIENCE", "SECURITY",
    "SERVICE", "SERVICES", "SHORT", "SMALL", "SPACE", "SPECIAL", "STRATEGIC",
    "STRIKE", "SUPPORT", "SYSTEM", "SYSTEMS", "TACTICAL", "TECHNICAL",
    "TECHNOLOGY", "TESTING", "TRAINING", "TRANSITION", "UNITED",
    "WARFIGHTING",
}
# EDUCATION and TRAINING were added past the task's prescribed list, found
# during this fix's own verification (#52 self-review, not the original
# review): PE 8101 "Training and Education Equipment" kept matching
# ALABAMA AEROSPACE AND AVIATION HIGH SCHOOL's filings via the boilerplate
# phrase "training, education and workforce" — two common English words
# co-occurring in unrelated aviation-workforce boilerplate, satisfying the
# letter of the multi_token rule while failing its purpose exactly the way
# the original single-token bug did. Same defect class, caught by testing
# the review's own named smell-test case rather than trusting the drop
# number alone. Disclosed per this sprint's substitution convention (see
# commit message and docs/superpowers/reviews/5c-gates-pre-failure.txt).

# parents[3] is the GovBudget project root (this file is at
# GovBudget/src/govbudget/influence/mentions.py). It was parents[4] until
# 2026-08-08, which resolved one level too high — outside the project — so
# _load_aliases hit its exists() guard and returned {} on every call, and the
# curated alias tier matched ZERO rows corpus-wide. Harmless while `alias` was
# only one of several signals; load-bearing once #52 made it a tier that
# qualifies a mention on its own.
_SEED_PATH = (
    Path(__file__).resolve().parents[3] / "dbt" / "seeds" / "program_aliases.csv"
)


def _load_aliases(
    seed_path: Path,
    valid_pe_blis: set[str],
) -> dict[str, list[str]]:
    """Load program_aliases.csv; return {pe_bli: [alias, ...]} for known pe_blis only."""
    result: dict[str, list[str]] = {}
    if not seed_path.exists():
        return result
    with seed_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pe_bli = (row.get("pe_bli") or "").strip()
            alias = (row.get("alias") or "").strip()
            if pe_bli and alias and pe_bli in valid_pe_blis:
                result.setdefault(pe_bli, []).append(alias)
    return result


def _candidate_terms_typed(
    title: str,
    pe_bli: str,
    aliases: list[str],
) -> list[tuple[str, str]]:
    """Generate (term, kind) candidate match terms for a single program.

    kind is one of "title_token", "pe_code", "alias". A title token whose
    uppercase form matches a curated alias is tagged "alias" (the curation is
    the stronger, human-verified signal, and a program's own name can
    legitimately be its own alias — e.g. JADC2 is both a title word and a
    seeded alias for 0604122D8Z).

    Returned list may be empty if no usable tokens found.
    """
    entries: list[tuple[str, str]] = []
    alias_upper = {a.upper() for a in aliases}
    # Title tokens
    tokens = re.split(r"[^A-Za-z0-9]+", title)
    for tok in tokens:
        up = tok.upper()
        if len(up) >= 5 and up not in GENERIC_WORDS:
            kind = "alias" if up in alias_upper else "title_token"
            entries.append((tok, kind))
    # PE/BLI code
    if pe_bli:
        entries.append((pe_bli, "pe_code"))
    # Aliases (multi-word phrases allowed)
    for alias in aliases:
        entries.append((alias, "alias"))
    return entries


def _candidate_terms(
    title: str,
    pe_bli: str,
    aliases: list[str],
) -> list[str]:
    """Flat term list (back-compat wrapper around _candidate_terms_typed).

    Terms: non-generic title tokens >=5 chars + pe_bli + aliases.
    """
    return [term for term, _kind in _candidate_terms_typed(title, pe_bli, aliases)]


def _build_word_boundary_re(term: str) -> re.Pattern:
    """Build a case-insensitive word-boundary regex for term."""
    escaped = re.escape(term)
    return re.compile(r"(?<![A-Za-z0-9])" + escaped + r"(?![A-Za-z0-9])", re.IGNORECASE)


# ── ROADMAP #176: a bare number is not a budget-line citation ────────────────
#
# An all-digit pe_bli ("2025", "14", "0145") matched ANY free-standing token
# of the same digits, and `pe_literal` — "PE code cited directly" on the site,
# one of the two tiers allowed to name a company in "Who gets it" — was
# published for years, dates, bill numbers and pieces of larger figures.
# Measured read-only 2026-09-25 on lda_activities.parquet: all 1,631
# `pe_literal` rows sat on 45 all-digit codes, none of the 4,253 code
# occurrences behind them carried a budget-line label, and a context census
# read them as a year ("Fiscal Year 2025", 3,099), a date
# ("September 30", 540), a bill or resolution number ("H.R. 20", 397), a
# public-law number ("P.L. 118-31", 87), a section/title number (51), a
# designator ("V-22", "CMS-4205-F", 47), part of a larger figure ("2,500",
# 24), a Federal Register cite (2) or other non-budget text (6). The
# alternative the ROADMAP entry floated — accept the code when the program's
# own title words sit nearby — was measured too: 38 rows had a title word
# within 100 characters, and none of the 38 named a budget line — bills,
# years and "2,500 megahertz" ("… (H.R. 4213); issues relating to border
# patrol aircraft.").
#
# So an all-digit code qualifies only where the filing NAMES it as a budget
# line: immediately after one of the labels below, optionally with "#", ":",
# "No." or "number" between. No filing in the 2026-09-25 corpus uses any of
# them, so the tier is empty on today's data; a code with letters in it
# (0604122D8Z, MD08) cannot be a year or a bill and keeps the plain rule.
_BUDGET_LINE_LABEL = (
    r"(?:BLIs?"
    r"|budget\s+lines?(?:\s+items?)?"
    r"|line\s+items?"
    r"|[PR]-?1\s+lines?(?:\s+items?)?"
    r"|program\s+elements?"
    r"|PE)"
)
_LABEL_TO_CODE = r"[\s#:.]*(?:(?:no|number)\.?[\s#:.]*)?"


def _is_bare_numeric_code(code: str) -> bool:
    """True for an all-digit pe_bli — the shape a year or a bill number shares."""
    return code.isdigit()


def _build_code_re(code: str) -> re.Pattern:
    """The pattern that counts as the program's code appearing in a filing.

    Alphanumeric codes: the plain word-boundary match. All-digit codes: only
    when a budget-line label names it (#176), and never as the head or the
    tail of a larger figure ("BLI 2,025", "BLI 2025.5", "BLI 20251").
    """
    if not _is_bare_numeric_code(code):
        return _build_word_boundary_re(code)
    return re.compile(
        r"(?<![A-Za-z0-9])" + _BUDGET_LINE_LABEL + _LABEL_TO_CODE
        + r"(?<![\d,])" + re.escape(code) + r"(?![A-Za-z0-9]|[.,]\d)",
        re.IGNORECASE,
    )


class ProgramTerms(list):
    """One code's [(term, compiled_regex, kind), ...] entries, plus the title
    groups the multi_token rule reads (R-DEC-176b).

    `title_groups` holds one frozenset of upper-cased "title_token" words per
    DISTINCT member title, in sorted-title order. A one-title code has one
    group, and the rule reads exactly as it did before shared codes were
    handled. It is a list so every existing reader of the (term, pattern,
    kind) tuples keeps working unchanged.
    """

    def __init__(self, entries, title_groups=()):
        super().__init__(entries)
        self.title_groups: tuple[frozenset[str], ...] = tuple(title_groups)


def build_program_terms(
    programs: Sequence[tuple[str, str]],
    *,
    seed_path: Path | None = None,
) -> dict[str, ProgramTerms]:
    """Build {pe_bli: ProgramTerms[(term, compiled_regex, kind), ...]}.

    kind is one of "title_token", "pe_code", "alias" — see
    _candidate_terms_typed. Consumed by find_mentions() to apply the
    evidence-tier rule (#52): a lone "title_token" match is not sufficient
    evidence on its own; "pe_code" and "alias" are.

    programs: sequence of (pe_bli, title) tuples. A code may appear on more
    than one row (a shared code); every member's title contributes its own
    title group — see the module docstring, "Shared codes".
    seed_path: path to program_aliases.csv (defaults to dbt/seeds/program_aliases.csv).

    Order-independent (R-DEC-176b): the result — its keys, each code's term
    order and its title groups — is the same for any order of `programs`.
    Codes are returned in sorted order and a shared code's member titles are
    read in sorted order, so the mention rows find_mentions emits do not
    move with the order dim_programs happens to return its rows in.
    """
    if seed_path is None:
        seed_path = _SEED_PATH
    titles_by_code: dict[str, set[str]] = defaultdict(set)
    for pe_bli, title in programs:
        titles_by_code[pe_bli].add(title or "")
    alias_map = _load_aliases(seed_path, set(titles_by_code))

    result: dict[str, ProgramTerms] = {}
    for pe_bli in sorted(titles_by_code):
        aliases = alias_map.get(pe_bli, [])
        # Deduplicate terms while preserving order. First occurrence wins —
        # title tokens are generated before the aliases list is appended, and
        # a title token that also matches a curated alias is already tagged
        # "alias" (see _candidate_terms_typed), so the first occurrence is
        # always the correctly-classified one. A one-title code's list is
        # exactly what it was before R-DEC-176b: its title words, its code,
        # its aliases. A shared code appends each later member's new words.
        seen: set[str] = set()
        compiled: list[tuple[str, re.Pattern, str]] = []
        groups: list[frozenset[str]] = []
        for title in sorted(titles_by_code[pe_bli]):
            entries = _candidate_terms_typed(title, pe_bli, aliases)
            group = frozenset(
                term.upper() for term, kind in entries if kind == "title_token"
            )
            if group and group not in groups:
                groups.append(group)
            for term, kind in entries:
                tu = term.upper()
                if tu not in seen:
                    seen.add(tu)
                    # The code tier reads its own pattern (#176): an all-digit
                    # code counts only where a budget-line label names it.
                    pattern = (
                        _build_code_re(term) if kind == "pe_code"
                        else _build_word_boundary_re(term)
                    )
                    compiled.append((term, pattern, kind))
        if compiled:
            result[pe_bli] = ProgramTerms(compiled, groups)
    return result


def _qualifying_title_tokens(
    matched: list[str],
    title_groups: tuple[frozenset[str], ...] | None,
) -> list[str]:
    """The matched title words that are multi_token evidence (#52, R-DEC-176b).

    A member title qualifies when >=2 of its own distinct words matched; the
    evidence is every matched word of every qualifying title, in `matched`'s
    order (the code's term order). `title_groups` None — a hand-built term
    list with no groups — reads the whole list as one title, the rule before
    R-DEC-176b.
    """
    if title_groups is None:
        return matched if len({t.upper() for t in matched}) >= 2 else []
    keep: set[str] = set()
    upper = {t.upper() for t in matched}
    for group in title_groups:
        hits = upper & group
        if len(hits) >= 2:
            keep |= hits
    return [t for t in matched if t.upper() in keep]


def find_mentions(
    activities: Sequence[dict],
    program_terms: dict[str, list[tuple[str, re.Pattern, str]]],
) -> list[dict]:
    """Find program mentions in a list of activity dicts.

    activities: list of dicts with 'filing_uuid' and 'description'. A filing
      may contribute more than one activity dict (lda_activities is grained
      on (filing_uuid, issue_code)) — all of a filing's descriptions are
      pooled before the evidence rule is applied, because the mention row is
      about the FILING, not a single activity line.
    program_terms: output of build_program_terms(). Codes are visited in
      the dict's order (sorted, from build_program_terms), so the returned
      rows' order is fixed by the activities' order alone.

    Evidence rule (#52 — see module docstring): a row is emitted for a given
    (filing_uuid, pe_bli) pair only when the pooled descriptions carry the
    exact pe_bli code ("pe_literal" — an all-digit code only where a
    budget-line label names it, #176), a curated alias ("alias"), or >=2
    distinct non-generic title tokens of one member's title ("multi_token";
    a shared code's members are read one title at a time, R-DEC-176b). A
    single title token is never sufficient on its own.

    Returns list of match dicts:
      {filing_uuid, pe_bli, matched_term, evidence_kind, description_snippet}
    At most one row per (filing_uuid, pe_bli) — the grain the mart declares.
    """
    descs_by_uuid: dict[str, list[str]] = defaultdict(list)
    for act in activities:
        uuid = act.get("filing_uuid") or ""
        desc = act.get("description") or ""
        if not uuid or not desc:
            continue
        descs_by_uuid[uuid].append(desc)

    results: list[dict] = []
    for uuid, descs in descs_by_uuid.items():
        for pe_bli, terms in program_terms.items():
            pe_code_match: str | None = None
            alias_match: str | None = None
            title_token_matches: list[str] = []
            snippet_source: str | None = None

            for term, pattern, kind in terms:
                hit_desc = next((d for d in descs if pattern.search(d)), None)
                if hit_desc is None:
                    continue
                if snippet_source is None:
                    snippet_source = hit_desc
                if kind == "pe_code":
                    pe_code_match = term
                elif kind == "alias":
                    if alias_match is None:
                        alias_match = term
                else:  # title_token
                    title_token_matches.append(term)

            # Priority: pe_literal > alias > multi_token (see module
            # docstring — this implementation's choice when more than one
            # tier qualifies at once).
            if pe_code_match is not None:
                matched_term, evidence_kind = pe_code_match, "pe_literal"
            elif alias_match is not None:
                matched_term, evidence_kind = alias_match, "alias"
            else:
                # >=2 distinct words of ONE member's title (R-DEC-176b: a
                # shared code's pair may not be split across two titles).
                evidence = _qualifying_title_tokens(
                    title_token_matches, getattr(terms, "title_groups", None)
                )
                if not evidence:
                    continue  # no qualifying evidence — a lone common word is not a naming
                matched_term = "|".join(evidence)
                evidence_kind = "multi_token"

            snippet = (snippet_source or "")[:120].replace("\n", " ").strip()
            results.append({
                "filing_uuid": uuid,
                "pe_bli": pe_bli,
                "matched_term": matched_term,
                "evidence_kind": evidence_kind,
                "description_snippet": snippet,
            })
    return results
