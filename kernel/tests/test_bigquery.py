"""BigQuery loaders: pure builders + fake-client execute paths. No network."""

import json

import pytest

from agentcom.kernel.bigquery import seed, connect, metrics, decisions, weakpoints, company
from agentcom.kernel.templates import TemplateRegistry
from agentcom.kernel.teardowns import TeardownRegistry
from agentcom.kernel.compliance import ComplianceRegistry

NOW = "2026-09-12T00:00:00+00:00"


class FakeClient:
    _fake = True

    def __init__(self):
        self._calls = []
        self.project = "test-proj"


@pytest.fixture
def templates():
    return TemplateRegistry()


@pytest.fixture
def teardowns():
    return TeardownRegistry()


@pytest.fixture
def compliance():
    return ComplianceRegistry()


@pytest.fixture
def fake():
    return FakeClient()


class TestBuilders:
    def test_template_rows_shape(self, templates):
        nodes, edges = seed.build_template_rows(
            templates.load("tpl-barber-gb"), NOW)
        assert nodes and edges
        for n in nodes:
            assert set(n) == {"node_id", "node_type", "properties_json",
                              "created_at", "updated_at", "confidence", "source"}
            json.loads(n["properties_json"])  # STRING, parseable
        assert nodes[0]["node_id"] == "TPL_BARBER_GB"
        assert any(n["node_id"] == "VERT_BARBER" for n in nodes)
        assert all(e["edge_type"] == "USES_STACK" for e in edges)

    def test_teardown_rows_shape(self, teardowns):
        nodes, edges, obs = seed.build_teardown_rows(
            teardowns.load("td-barber-gb"), NOW)
        assert any(n["node_id"] == "PAIN_BARBER_01" for n in nodes)
        assert any(e["edge_type"] == "FIXED_BY" for e in edges)
        assert all(o["metric_name"].startswith("leak.") for o in obs)

    def test_legislation_skips_nonlaw(self, compliance):
        nodes, _ = seed.build_legislation_rows(compliance.load_all(), NOW)
        ids = [n["node_id"] for n in nodes]
        assert not any("NONLAW" in i for i in ids)
        assert "LAW_FGAS" in ids

    def test_company_node(self):
        n, e = company.company_node("COMP-DBE371FA", "Agentcom",
                                    "agent-commerce", "GB",
                                    "tpl-dropship-gb", NOW)
        assert n["node_id"] == "COMP_DBE371FA"
        assert e["edge_type"] == "SEEDED_FROM"
        assert company.operates_in_edge("COMP_DBE371FA", "GB", NOW)[
            "target_node"] == "COUNTRY_GB"

    def test_weakpoint_propose_is_proposed(self):
        n, edges = weakpoints.propose_pain(
            "tpl-barber-gb", "test pain", "mech", ["http://x"], NOW)
        assert json.loads(n["properties_json"])["verification"] == "PROPOSED"
        assert edges[0]["edge_type"] == "HAS_PAIN"

    def test_metrics_builders(self):
        obs = metrics.stack_price_observations("TOOL_X", {"monthly_gbp": 40.0}, NOW)
        assert obs[0]["metric_name"] == "price.monthly_gbp"
        assert metrics.price_drift_alert("TOOL_X", "m", 100.0, 105.0, NOW) is None
        assert metrics.price_drift_alert("TOOL_X", "m", 100.0, 120.0, NOW) is not None
        vac = metrics.ons_vacancy_observations({"Q": 5090.0}, NOW)
        assert vac[0]["node_id"] == "SIC_Q"


class TestExecuteFake:
    def test_merge_nodes_records(self, fake):
        n = seed.node("N1", "template", {}, NOW)
        assert connect.merge_nodes(fake, "drop", [n]) == 1
        assert fake._calls[0][0] == "merge_nodes"

    def test_edges_and_observations_record(self, fake):
        e = seed.edge("E1", "A", "B", "HAS_PAIN", NOW)
        o = seed.observation("A", "m", 1.0, NOW)
        assert connect.insert_edges_new(fake, "drop", [e]) == 1
        assert connect.insert_observations(fake, "drop", [o]) == 1

    def test_empty_noops(self, fake):
        assert connect.merge_nodes(fake, "drop", []) == 0
        assert connect.insert_edges_new(fake, "drop", []) == 0
        assert connect.insert_observations(fake, "drop", []) == 0

    def test_audit_export_maps_decisions(self, fake):
        class E:
            entry_id = "AUD-1"; actor = "agent:x"; task_id = "A-1"
            resource = "r"; decision = "ALLOW"; reason = "ok"
            details = {"action": "domain.check", "company_id": "COMP_X"}
        assert decisions.export_audit(fake, "drop", [E()], NOW) == 1

    def test_audit_export_skips_non_decisions(self, fake):
        class E:
            entry_id = "AUD-2"; actor = "a"; task_id = None
            resource = ""; decision = None; reason = None; details = {}
        assert decisions.export_audit(fake, "drop", [E()], NOW) == 0

    def test_builders_emit_iso_strings(self):
        n = seed.node("N1", "template", {}, NOW)
        assert isinstance(n["created_at"], str) and "T" in n["created_at"]

    def test_no_doubled_prefixes(self):
        from agentcom.kernel.templates import TemplateRegistry
        from agentcom.kernel.teardowns import TeardownRegistry
        for tpl in TemplateRegistry().load_all():
            nodes, edges = seed.build_template_rows(tpl, NOW)
            for n in nodes + edges:
                for v in (n.get("node_id", ""), n.get("source_node", ""),
                          n.get("target_node", "")):
                    assert "FIX_FIX" not in v and "LAW_LAW" not in v
                    assert "LAW_LEG" not in v
        for td in TeardownRegistry().load_all():
            nodes, edges, _ = seed.build_teardown_rows(td, NOW)
            for n in nodes + edges:
                for v in (n.get("node_id", ""), n.get("source_node", ""),
                          n.get("target_node", "")):
                    assert "FIX_FIX" not in v
