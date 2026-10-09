"""Blueprints: free-only catalogs, regulator coverage, specs present, index valid."""

import json
from pathlib import Path

import pytest

ROOT = Path("/root/agentcom")
BP = ROOT / "blueprints"

CATALOGS = [
    BP / "data-sources/govt-uk.json",
    BP / "data-sources/commercial.json",
    BP / "data-sources/ai.json",
]
REPORTS = BP / "data-sources/reports.json"
REGULATORS = ROOT / "kernel/compliance/regulators.json"
REQUIRED_FIELDS = {"id", "name", "url", "access", "auth", "cost", "basis", "status"}
AUTH_ENUM = {"none", "key-free-signup", "key-billing", "verify-first"}
REG_TYPES = {"regulator", "licensing-body", "trade-body", "guidance", "none"}


def load_catalog(path):
    key = "sources" if path.name != "reports.json" else "reports"
    reg_key = "regulators"
    data = json.loads(path.read_text())
    return data.get(key, data.get(reg_key, []))


class TestCatalogs:
    def test_files_exist(self):
        for p in CATALOGS + [REPORTS, REGULATORS]:
            assert p.exists(), f"missing {p}"

    def test_required_fields(self):
        for p in CATALOGS:
            for entry in load_catalog(p):
                missing = REQUIRED_FIELDS - set(entry)
                assert not missing, f"{p.name}/{entry.get('id')}: missing {missing}"

    def test_free_only_hard_rule(self):
        for p in CATALOGS:
            for entry in load_catalog(p):
                assert entry["cost"] == "free", f"{entry['id']} is not free"

    def test_auth_enum(self):
        for p in CATALOGS:
            for entry in load_catalog(p):
                assert entry["auth"] in AUTH_ENUM, f"{entry['id']}: bad auth"

    def test_status_enum(self):
        for p in CATALOGS:
            for entry in load_catalog(p):
                assert entry["status"] in ("verified", "to-verify")

    def test_https_urls(self):
        for p in CATALOGS:
            for entry in load_catalog(p):
                assert entry["url"].startswith("https://"), entry["id"]

    def test_key_gated_flagged_for_human(self):
        for p in CATALOGS:
            for entry in load_catalog(p):
                if entry["auth"] in ("key-free-signup", "key-billing", "verify-first"):
                    notes = entry.get("notes", "").lower()
                    assert "h-task" in notes or "verify" in notes or "signup" in notes, \
                        f"{entry['id']}: gated auth without H-task note"

    def test_relevance_resolves(self):
        from agentcom.kernel.templates import TemplateRegistry
        known = set(TemplateRegistry().list_ids()) | {"all"}
        for p in CATALOGS:
            for entry in load_catalog(p):
                for ref in entry.get("relevance", []):
                    assert ref in known, f"{entry['id']}: unknown {ref}"


class TestReports:
    def test_cadence_present(self):
        for r in load_catalog(REPORTS):
            assert r.get("cadence") and r.get("covers") and r.get("url")

    def test_anchor_reports_present(self):
        ids = {r["id"] for r in load_catalog(REPORTS)}
        for must in ("ons-jobs-vacancies", "skills-england", "deloitte-retail",
                     "pwc-construction", "cma-funerals-review"):
            assert must in ids


class TestRegulators:
    def test_types_and_basis(self):
        for r in load_catalog(REGULATORS):
            assert r["type"] in REG_TYPES
            assert r["basis"] in ("verified-2026", "well-established", "template-analysis")

    def test_every_vertical_covered(self):
        from agentcom.kernel.templates import TemplateRegistry
        verticals = {t.vertical for t in TemplateRegistry().load_all()}
        covered = {v for r in load_catalog(REGULATORS) for v in r.get("verticals", [])}
        assert verticals <= covered, f"uncovered: {verticals - covered}"

    def test_none_entries_honest(self):
        for r in load_catalog(REGULATORS):
            if r["type"] == "none":
                assert "no " in r["name"].lower() or "No " in r.get("notes", "")


class TestSpecs:
    def test_spec_files_exist(self):
        for name in ("ingestion-pipeline.md", "weakpoint-mining.md",
                     "stack-tracking.md", "scoring-v2.md"):
            assert (BP / "specs" / name).exists()

    def test_master_index_valid(self):
        idx = json.loads((BP / "MASTER_INDEX.json").read_text())
        for a in idx["artifacts"]:
            assert (ROOT / a["path"]).exists(), f"index references missing {a['path']}"
        orders = sorted({a["bq_order"] for a in idx["artifacts"]})
        assert orders[0] == 0  # plan itself is order 0
