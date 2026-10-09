"""Analysis: rollups, readiness, opportunity — all computed, all tested."""

import pytest

from agentcom.kernel.analysis import (
    pattern_rollup, readiness_score, readiness_all, opportunity_ranking,
    ONS_JOBS_SNAPSHOT, ONS_SNAPSHOT_SOURCE)
from agentcom.kernel.templates import TemplateRegistry
from agentcom.kernel.teardowns import TeardownRegistry


@pytest.fixture
def templates():
    return TemplateRegistry()


@pytest.fixture
def teardowns():
    return TeardownRegistry()


class TestPatternRollup:
    def test_every_template_in_exactly_one_pattern(self, templates, teardowns):
        rollup = pattern_rollup(templates, teardowns)
        seen = [t for node in rollup.values() for t in node["templates"]]
        assert sorted(seen) == templates.list_ids()
        assert len(seen) == len(set(seen))

    def test_job_led_rollup_content(self, templates, teardowns):
        node = pattern_rollup(templates, teardowns)["job-led"]
        assert {"tpl-builder-gb", "tpl-electrician-gb", "tpl-hvac-gb",
                "tpl-tree-surgeon-gb", "tpl-garage-gb"} <= set(node["templates"])
        assert node["margin_leaks"] > 0 and node["compliance_count"] > 0

    def test_snapshot_source_stated(self):
        assert "ONS" in ONS_SNAPSHOT_SOURCE and "2026" in ONS_SNAPSHOT_SOURCE


class TestReadiness:
    def test_scores_bounded_and_explained(self, teardowns):
        for td in teardowns.load_all():
            r = readiness_score(td)
            assert 0.0 <= r["score"] <= 100.0
            assert r["deductions"]  # physical-fulfillment line always present

    def test_ceiling_holds(self, teardowns):
        for r in readiness_all(teardowns):
            assert r["score"] <= 90.0  # coordination only, never full autonomy

    def test_ranking_sorted(self, teardowns):
        ranked = readiness_all(teardowns)
        assert len(ranked) == len(teardowns.load_all())
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)


class TestOpportunity:
    def test_ranking_covers_all_templates(self, templates, teardowns):
        ranked = opportunity_ranking(templates, teardowns)
        assert len(ranked) == len(templates.list_ids())
        assert ranked[0]["opportunity"] >= ranked[-1]["opportunity"]

    def test_care_outranks_niche(self, templates, teardowns):
        ranked = {r["template_id"]: r["opportunity"]
                  for r in opportunity_ranking(templates, teardowns)}
        assert ranked["tpl-care-gb"] > ranked["tpl-tree-surgeon-gb"]

    def test_custom_vacancies_respected(self, templates, teardowns):
        ranked = opportunity_ranking(templates, teardowns,
                                     vacancies={"F": 10000.0})
        assert ranked[0]["template_id"] in ("tpl-builder-gb", "tpl-electrician-gb",
                                            "tpl-hvac-gb")
