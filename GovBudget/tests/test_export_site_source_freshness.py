"""site_meta.source_freshness — ROADMAP #8.

`config.MANIFEST_PATH` had existed since Phase 1 and the exporter never opened
it. site_meta carried `built_at` — when the SITE was built — and nothing about
when the DATA underneath it was downloaded, so a 2026-08-31 build over a
corpus fetched 2026-06-11 stamped the export date on 39,288 derived citations
and /methodology/ published "Update cadence: monthly" over an 81-day-old
corpus. These tests pin the block that makes the fetch date renderable.
"""

import json

import pytest

from govbudget import export_site
from govbudget.export_site import (
    _DECLARED_CADENCE,
    _FRESHNESS_GROUPS,
    _source_freshness_block,
)


def _write_manifest(tmp_path, records):
    p = tmp_path / "manifest.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in records))
    return p


@pytest.fixture
def manifest_at(tmp_path, monkeypatch):
    """Point config.MANIFEST_PATH at a fixture manifest."""

    def _set(records):
        path = _write_manifest(tmp_path, records)
        from govbudget import config

        monkeypatch.setattr(config, "MANIFEST_PATH", path)
        return path

    return _set


class TestDeclaredCadence:
    def test_every_declared_cadence_is_a_word_the_gate_knows(self):
        """The gate ages `monthly|quarterly|annual|biennial`; None = no claim."""
        allowed = {None, "monthly", "quarterly", "annual", "biennial"}
        for ds, cad in _DECLARED_CADENCE.items():
            assert cad in allowed, f"{ds} declares unknown cadence {cad!r}"

    def test_every_group_member_is_a_declared_dataset(self):
        for group, members in _FRESHNESS_GROUPS.items():
            assert members, f"{group} has no members"
            for m in members:
                assert m in _DECLARED_CADENCE, f"{group} names undeclared {m}"


class TestSourceFreshnessBlock:
    def test_newest_download_wins_per_dataset(self, manifest_at):
        manifest_at([
            {"dataset": "contracts", "file_name": "old.zip",
             "downloaded_at": "2026-01-01T00:00:00+00:00"},
            {"dataset": "contracts", "file_name": "new.zip",
             "downloaded_at": "2026-06-11T11:50:15+00:00"},
        ])
        block = _source_freshness_block()
        ds = block["datasets"]["contracts"]
        assert ds["newest_downloaded_at"] == "2026-06-11T11:50:15+00:00"
        assert ds["newest_file_name"] == "new.zip"
        assert ds["declared_cadence"] == "monthly"
        assert ds["files"] == 2

    def test_group_as_of_is_the_stalest_member(self, manifest_at):
        """One fresh dataset must not vouch for two stale ones."""
        manifest_at([
            {"dataset": "contracts", "file_name": "c.zip",
             "downloaded_at": "2026-06-11T11:50:15+00:00"},
            {"dataset": "assistance", "file_name": "a.zip",
             "downloaded_at": "2026-08-30T00:00:00+00:00"},
            {"dataset": "subawards", "file_name": "s.zip",
             "downloaded_at": "2026-08-31T00:00:00+00:00"},
        ])
        block = _source_freshness_block()
        grp = block["groups"]["usaspending"]
        assert grp["as_of"] == "2026-06-11", "as_of took the newest, not the stalest"
        assert grp["newest_file_name"] == "c.zip"
        assert grp["stalest_dataset"] == "contracts"
        assert grp["declared_cadence"] == "monthly"
        assert grp["datasets"] == ["assistance", "contracts", "subawards"]

    # Task 29 fix round 1 (CRITICAL). /methodology/ rendered "this corpus was
    # fetched 2026-06-11" once the 2026-09-06 FY2026 contract and assistance
    # archives (fetched 2026-09-24) were adopted: the group date is the
    # SUBAWARDS' newest download, and the sentence gave it to the whole corpus.
    # The page now names the part the date belongs to, so the name must be the
    # member whose newest download IS that date — for every ordering of the
    # three members' fetch dates, not just today's.
    @pytest.mark.parametrize(
        "order",
        [
            ("assistance", "contracts", "subawards"),
            ("assistance", "subawards", "contracts"),
            ("contracts", "assistance", "subawards"),
            ("contracts", "subawards", "assistance"),
            ("subawards", "assistance", "contracts"),
            ("subawards", "contracts", "assistance"),
        ],
    )
    def test_stalest_dataset_names_the_member_the_date_belongs_to(
        self, manifest_at, order
    ):
        """`order[0]` is fetched first, `order[2]` last; each member also has
        an OLDER file (a fiscal year fetched earlier), so the rule under test
        is the stalest of the per-dataset NEWEST downloads, not the oldest
        file."""
        newest = ["2026-06-11T12:06:10+00:00", "2026-08-01T00:00:00+00:00",
                  "2026-09-24T04:34:55+00:00"]
        records = []
        for ds, at in zip(order, newest):
            records.append({"dataset": ds, "file_name": f"{ds}-old.zip",
                            "downloaded_at": "2026-06-10T15:58:52+00:00"})
            records.append({"dataset": ds, "file_name": f"{ds}-new.zip",
                            "downloaded_at": at})
        manifest_at(records)
        grp = _source_freshness_block()["groups"]["usaspending"]
        stalest = order[0]
        assert grp["stalest_dataset"] == stalest
        assert grp["as_of"] == "2026-06-11"
        assert grp["newest_downloaded_at"] == newest[0]
        assert grp["newest_file_name"] == f"{stalest}-new.zip"
        # The claim the page makes: no other member's newest download is older.
        datasets = _source_freshness_block()["datasets"]
        for ds in grp["datasets"]:
            assert (
                datasets[ds]["newest_downloaded_at"]
                >= datasets[grp["stalest_dataset"]]["newest_downloaded_at"]
            )

    def test_stalest_dataset_on_an_exact_tie_is_deterministic(self, manifest_at):
        """Two members fetched at the same instant are equally stale; either
        name is true, and the block must not flip between builds. Ties break
        by dataset name."""
        at = "2026-06-11T12:06:10+00:00"
        manifest_at([
            {"dataset": "subawards", "file_name": "s.zip", "downloaded_at": at},
            {"dataset": "contracts", "file_name": "c.zip", "downloaded_at": at},
            {"dataset": "assistance", "file_name": "a.zip",
             "downloaded_at": "2026-09-24T04:29:08+00:00"},
        ])
        grp = _source_freshness_block()["groups"]["usaspending"]
        assert grp["stalest_dataset"] == "contracts"
        assert grp["as_of"] == "2026-06-11"

    def test_a_single_member_group_names_that_member(self, manifest_at):
        manifest_at([
            {"dataset": "subawards", "file_name": "s.zip",
             "downloaded_at": "2026-06-11T12:06:10+00:00"},
        ])
        grp = _source_freshness_block()["groups"]["usaspending"]
        assert grp["datasets"] == ["subawards"]
        assert grp["stalest_dataset"] == "subawards"

    def test_undeclared_dataset_raises_rather_than_defaulting(self, manifest_at):
        """A new source is a decision; defaulting makes it silently."""
        manifest_at([
            {"dataset": "contracts", "file_name": "c.zip",
             "downloaded_at": "2026-06-11T11:50:15+00:00"},
            {"dataset": "brand_new_feed", "file_name": "x.zip",
             "downloaded_at": "2026-08-31T00:00:00+00:00"},
        ])
        with pytest.raises(ValueError) as exc:
            _source_freshness_block()
        assert "brand_new_feed" in str(exc.value)
        assert "_DECLARED_CADENCE" in str(exc.value)

    def test_missing_manifest_yields_empty_block_not_a_crash(self, tmp_path, monkeypatch):
        from govbudget import config

        monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "nope.jsonl")
        assert _source_freshness_block() == {"datasets": {}, "groups": {}}

    def test_real_manifest_declares_every_dataset_it_holds(self):
        """The shipped manifest must not have outgrown the cadence table."""
        block = _source_freshness_block()
        assert block["datasets"], "the repo manifest produced no datasets"
        for ds in block["datasets"]:
            assert ds in _DECLARED_CADENCE
