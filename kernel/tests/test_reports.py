"""Reports: schema-validated structure, honest tables, working renderer."""

import json
from pathlib import Path

import pytest

from agentcom.kernel.reports import ReportRegistry, VALID_KINDS, render_markdown

REPORT = Path("/root/agentcom/kernel/reports/state-of-reports.json")


@pytest.fixture
def report():
    return json.loads(REPORT.read_text())


@pytest.fixture
def registry():
    return ReportRegistry()


class TestReportStructure:
    def test_validates_clean(self, registry, report):
        assert registry.validate(report) == []

    def test_spine_covers_drop_pattern(self, registry, report):
        kinds = {s["kind"] for s in report["sections"]}
        for required in ("executive-summary", "inventory", "census", "proof",
                         "gaps", "tiers", "honesty", "next-steps", "sources"):
            assert required in kinds, required

    def test_rejects_bad_kind(self, registry):
        assert any("bad kind" in e for e in
                   registry.validate({"report_id": "x", "title": "x", "date": "x",
                                      "status": "x",
                                      "sections": [{"kind": "vibes", "heading": "h"}]}))

    def test_rejects_ragged_tables(self, registry):
        bad = {"report_id": "x", "title": "x", "date": "x", "status": "x",
               "sections": [{"kind": "gaps", "heading": "h",
                             "tables": [{"columns": ["a", "b"], "rows": [["only-a"]]}]}]}
        assert any("mismatch" in e for e in registry.validate(bad))


class TestRenderer:
    def test_renders_all_sections(self, report):
        md = render_markdown(report)
        for s in report["sections"]:
            assert s["heading"] in md
        assert md.startswith("# ")

    def test_tables_render(self, report):
        md = render_markdown(report)
        assert "| table | type | rows | purpose |" in md

    def test_queries_render_with_results(self, report):
        md = render_markdown(report)
        assert "```sql" in md and "→ " in md

    def test_rendered_file_matches(self, report):
        on_disk = Path("/root/agentcom/STATE_OF_REPORTS.md").read_text()
        assert render_markdown(report) + "\n" == on_disk
