"""Task 17c — site_meta.org_absences, the payload that replaces a false sentence.

Until this task every org with no loaded FY2026 J-book detail got the same
coverage note: "…J-book, which is not yet ingested". That presupposes a book
exists. For FY2026 it was false on 5 pages (IG published no RDT&E or
procurement justification book at all; DEFW publishes none for its
reconciliation / undistributed / roll-up rows) and imprecise on 14 more (the
DHP book WAS downloaded and carries no jb-2009 payload).

`export_site._org_absences` is the reader half of the probe record written by
`edition_probe.record_org_absences`. These cases pin the contract the site
renders from:

  * keyed by org, carrying ONLY {rule, fy, checked_on, checked_url} — the
    operator's `reason` prose is never published;
  * scoped to ONE edition;
  * {} when nothing is recorded (the genuinely-unprobed state, which is what
    the generic "not yet ingested" wording is for);
  * a hard failure on a rule the site has no sentence for, because silently
    dropping an absence restores the false wording it replaced.

The writer and the reader are exercised against each other (no hand-built
manifest in the round-trip case) so the two halves cannot drift apart.
"""
import json

import pytest

from govbudget.export_site import _org_absences
from govbudget.jbooks.edition_probe import ORG_ABSENCE_RULES, record_org_absences


def _entry(org: str, rule: str, *, reason: str = "probed, see the run log",
           checked_on: str = "2026-09-12",
           checked_url: str = "https://comptroller.war.gov/x") -> dict:
    return {"org": org, "rule": rule, "reason": reason,
            "checked_url": checked_url, "checked_on": checked_on}


def test_absences_are_keyed_by_org_and_publish_no_reason_prose(tmp_path):
    manifest = tmp_path / "edition_manifest.json"
    record_org_absences(manifest, 2026, [
        _entry("IG", "no-justification-book-published",
               reason="index publishes only OIG_OP-5.pdf; internal note, not for readers",
               checked_url="https://comptroller.war.gov/Budget-Materials/"),
        _entry("DEFW", "summary-line-only"),
        _entry("DHA", "book-carries-no-embedded-xml",
               checked_url="https://comptroller.war.gov/…/00-DHP_Vols_I_and_II_PB26.pdf"),
    ])

    got = _org_absences(manifest, 2026)

    assert sorted(got) == ["DEFW", "DHA", "IG"]
    assert got["IG"] == {
        "rule": "no-justification-book-published",
        "fy": 2026,
        "checked_on": "2026-09-12",
        "checked_url": "https://comptroller.war.gov/Budget-Materials/",
    }
    assert got["DHA"]["rule"] == "book-carries-no-embedded-xml"
    # The reason is the operator's audit trail — HTTP probes, byte counts,
    # backlog cross-references. Every word the site renders comes from the
    # rule and the org code, so none of that prose may reach the payload.
    for entry in got.values():
        assert set(entry) == {"rule", "fy", "checked_on", "checked_url"}
        assert "internal note" not in json.dumps(entry)


def test_absences_are_scoped_to_one_edition(tmp_path):
    manifest = tmp_path / "edition_manifest.json"
    record_org_absences(manifest, 2025, [_entry("SDA", "summary-line-only")])
    record_org_absences(manifest, 2026, [_entry("IG", "no-justification-book-published")])

    assert sorted(_org_absences(manifest, 2026)) == ["IG"]
    assert sorted(_org_absences(manifest, 2025)) == ["SDA"]
    # And each entry carries the edition it belongs to, because every sentence
    # the site renders from it names that year ("No FY2025 …"). Typed on the
    # TypeScript side instead, the year rots the day JBOOK_FY rolls over.
    assert _org_absences(manifest, 2025)["SDA"]["fy"] == 2025
    assert _org_absences(manifest, 2026)["IG"]["fy"] == 2026


def test_absent_manifest_or_section_is_empty_not_an_error(tmp_path):
    # No file at all — a fresh checkout, or an export run before any probe.
    assert _org_absences(tmp_path / "missing.json", 2026) == {}
    # A manifest with editions but no org_absences section.
    manifest = tmp_path / "edition_manifest.json"
    manifest.write_text(json.dumps({"editions": {"2026": {"status": "loaded"}}}))
    assert _org_absences(manifest, 2026) == {}
    # A manifest whose org_absences section names other editions only.
    record_org_absences(manifest, 2024, [_entry("IG", "summary-line-only")])
    assert _org_absences(manifest, 2026) == {}


def test_an_unknown_rule_stops_the_export(tmp_path):
    """A rule the site has no sentence for must not be dropped silently.

    Dropping it would put the org back on the generic "not yet ingested"
    branch — the exact false sentence this payload exists to end — and no
    gate could tell that state from "nobody has probed this org yet".
    """
    manifest = tmp_path / "edition_manifest.json"
    manifest.write_text(json.dumps({"org_absences": {"2026": [
        {"org": "IG", "rule": "book-is-classified", "reason": "r",
         "checked_url": "https://x", "checked_on": "2026-09-12"},
    ]}}))

    with pytest.raises(ValueError, match="book-is-classified"):
        _org_absences(manifest, 2026)


def test_every_recorded_rule_round_trips(tmp_path):
    """The writer's vocabulary and the reader's are ONE constant.

    record_org_absences rejects a rule outside ORG_ABSENCE_RULES and
    _org_absences raises on one, so a rule added to the vocabulary without a
    site sentence cannot reach a page by either door.
    """
    manifest = tmp_path / "edition_manifest.json"
    record_org_absences(manifest, 2026, [
        _entry(f"ORG{i}", rule) for i, rule in enumerate(ORG_ABSENCE_RULES)
    ])

    got = _org_absences(manifest, 2026)

    assert {e["rule"] for e in got.values()} == set(ORG_ABSENCE_RULES)


def test_the_shipped_manifest_records_the_three_fy2026_absences():
    """The live record, read the way the export reads it.

    Not a fixture: this is the claim the site makes on 19 program pages
    (DHA 14, DEFW 4, IG 1), and each org's RULE is what selects its sentence.
    Recorded 2026-09-12 by Task 17a's scripted probe.
    """
    got = _org_absences()

    assert got["IG"]["rule"] == "no-justification-book-published"
    assert got["DEFW"]["rule"] == "summary-line-only"
    assert got["DHA"]["rule"] == "book-carries-no-embedded-xml"
    for org, entry in got.items():
        assert entry["checked_on"], org
        assert entry["checked_url"].startswith("https://"), org
