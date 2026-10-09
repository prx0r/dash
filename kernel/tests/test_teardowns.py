"""Teardowns: every template interrogated, stats have basis, pains map to fixes."""

import pytest

from agentcom.kernel.teardowns import TeardownRegistry, FIX_IDS
from agentcom.kernel.templates import TemplateRegistry


@pytest.fixture
def registry():
    return TeardownRegistry()


class TestTeardownCoverage:
    def test_every_template_has_teardown(self, registry):
        templates = set(TemplateRegistry().list_ids())
        teardowns = {t.template_id for t in registry.load_all()}
        assert templates == teardowns, f"missing: {templates - teardowns}"

    def test_ids_match_filenames(self, registry):
        for tid in registry.list_ids():
            assert registry.load(tid).teardown_id == tid


class TestTeardownValidity:
    def test_all_load(self, registry):
        assert len(registry.load_all()) >= 24

    def test_all_stats_have_basis(self, registry):
        for td in registry.load_all():
            for leak in td.raw.get("margin_leaks", []):
                if leak.get("stat"):
                    assert leak["stat_basis"] in (
                        "verified-2026", "govt-data", "template-analysis")

    def test_all_pains_map_to_known_fixes(self, registry):
        for td in registry.load_all():
            for p in td.raw.get("pain_ranking", []):
                assert p["fix_id"] in FIX_IDS

    def test_ranks_contiguous(self, registry):
        for td in registry.load_all():
            ranks = sorted(p["rank"] for p in td.raw["pain_ranking"])
            assert ranks == list(range(1, len(ranks) + 1))

    def test_scaling_wall_present(self, registry):
        for td in registry.load_all():
            wall = td.raw.get("scaling_wall", {})
            assert wall.get("breaks_at") and wall.get("bottleneck")


class TestPainIndex:
    def test_every_fix_shared_by_multiple_templates(self, registry):
        index = registry.pain_index()
        for fix_id in FIX_IDS:
            assert len(index[fix_id]) >= 2, f"{fix_id} shared by <2 templates"

    def test_noshow_clusters_on_booking_verticals(self, registry):
        index = registry.pain_index()
        holders = set(index["FIX-NOSHOW"])
        assert {"tpl-barber-gb", "tpl-restaurant-gb", "tpl-hotel-gb"} <= holders

    def test_marketplace_tax_clusters(self, registry):
        index = registry.pain_index()
        holders = set(index["FIX-MARKETPLACE-TAX"])
        assert {"tpl-restaurant-gb", "tpl-hotel-gb", "tpl-reseller-gb"} <= holders

    def test_compliance_drift_clusters_on_regulated(self, registry):
        index = registry.pain_index()
        holders = set(index["FIX-COMPLIANCE-DRIFT"])
        assert {"tpl-vet-gb", "tpl-hvac-gb", "tpl-care-gb"} <= holders
