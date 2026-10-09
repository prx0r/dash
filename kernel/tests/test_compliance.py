"""Compliance: every vertical has law behind it; no invented statutes."""

import pytest

from agentcom.kernel.compliance import ComplianceRegistry, ALLOWED_BASIS
from agentcom.kernel.templates import TemplateRegistry


@pytest.fixture
def compliance():
    return ComplianceRegistry()


class TestCompliancePack:
    def test_valid_basis_only(self, compliance):
        for entry in compliance.load_all():
            assert entry.basis in ALLOWED_BASIS, f"{entry.id}: bad basis"

    def test_verified_entries_have_sources(self, compliance):
        for entry in compliance.verified():
            assert entry.raw.get("source_url"), f"{entry.id}: verified without source"

    def test_every_vertical_covered(self, compliance):
        verticals = {t.vertical for t in TemplateRegistry().load_all()}
        covered = {v for e in compliance.load_all() for v in e.verticals}
        assert verticals <= covered, f"uncovered: {verticals - covered}"

    def test_design_rules_labelled_not_law(self, compliance):
        ids = {e.id for e in compliance.load_all()}
        assert "NONLAW-SOCIAL-CREATION" in ids
        assert "NONLAW-MONEY-APPROVAL" in ids
        for e in compliance.load_all():
            if e.id.startswith("NONLAW-"):
                assert e.basis == "template-analysis"

    def test_funeral_notes_no_licensing_regime(self, compliance):
        funerals = [e for e in compliance.load_all() if e.id == "LEG-CMA-FUNERALS"]
        assert len(funerals) == 1
        assert "NO licensing regime" in funerals[0].raw.get("requires", [""])[-1] or \
            "not in force" in json_dumps(funerals[0].raw)

    def test_count_sane(self, compliance):
        assert len(compliance.load_all()) >= 20


def json_dumps(obj):
    import json
    return json.dumps(obj)
