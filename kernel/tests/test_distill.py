"""Distillprotocol: ops valid, executors pure, chain runs end to end."""

import pytest

from agentcom.kernel.distill import DistillRegistry, run_chain
from agentcom.kernel.distill import executors as ex

EXPECTED_OPS = [
    "distill-sprawl-scan",
    "distill-cluster",
    "distill-snowball",
    "distill-gate-check",
    "distill-campaign-compile",
    "distill-refine",
]


@pytest.fixture
def registry():
    return DistillRegistry()


class TestOpDefinitions:
    def test_all_ops_present(self, registry):
        assert registry.list_ids() == sorted(EXPECTED_OPS)

    def test_op_contract(self, registry):
        for op in registry.load_all():
            assert op["version"].startswith("v")
            assert 0 <= op["side_effect"] <= 5
            assert isinstance(op["deterministic"], bool)
            assert op["sources"]  # every op cites its drop source

    def test_unknown_op_raises(self, registry):
        with pytest.raises(KeyError):
            registry.load("distill-nope")


class TestSprawlScan:
    def test_empty_tables_flagged(self):
        out = ex.sprawl_scan([
            {"table": "graph_nodes", "kind": "graph", "country": "ALL", "rows": 398},
            {"table": "keyword_data", "kind": "evidence", "country": "ALL", "rows": 0},
        ])
        assert any(f["table"] == "keyword_data" and f["flag"] == "EMPTY"
                   for f in out["flags"])
        assert any(p["kind"] == "graph" for p in out["pools"])

    def test_empty_sprawl_lists_known_gaps(self):
        out = ex.sprawl_scan([{"table": "x", "rows": 0}])
        assert "Real CPC data" in str(out["coverage_gaps"])


class TestCluster:
    def test_shared_signals_bucket(self):
        out = ex.cluster([
            {"id": "a", "mechanism": "M1", "country": "NO"},
            {"id": "b", "mechanism": "M1", "country": "NO"},
            {"id": "c", "mechanism": "M9", "country": "GB"},
        ])
        assert len(out["theses"]) == 1
        assert out["theses"][0]["status"] == "PROPOSED"
        assert sorted(out["theses"][0]["members"]) == ["a", "b"]

    def test_singletons_dropped(self):
        out = ex.cluster([{"id": "a", "mechanism": "M1"}])
        assert out["theses"] == []


class TestSnowball:
    def test_version_bumps_and_history_kept(self):
        t0 = {"thesis_id": "TH-X", "version": 3, "confidence": 0.6,
              "observations": [{"id": "OBS-1", "basis": "template-analysis"}],
              "corrections": []}
        t1 = ex.snowball(t0, [{"basis": "verified-2026", "claim": "cpc=0.85"}])
        assert t1["version"] == 4
        assert len(t1["observations"]) == 2
        assert t1["prior_version"]["n_observations"] == 1
        assert t1["confidence"] > 0.6  # verified evidence raises it

    def test_correction_downgrade(self):
        t1 = {"thesis_id": "TH-X", "version": 1, "confidence": 0.8,
              "observations": [], "corrections": []}
        t2 = ex.snowball_correct(t1, "narrow-scope", "heat pumps whole-unit out")
        assert t2["corrections"][0]["type"] == "narrow-scope"
        t3 = ex.snowball_correct(t1, "downgrade", "overclaim")
        assert t3["confidence"] < 0.8

    def test_bad_correction_rejected(self):
        with pytest.raises(AssertionError):
            ex.snowball_correct({}, "vibes", "x")


class TestGateCheck:
    def _gates(self, state="PASS"):
        return {g: state for g in ex.GATES}

    def test_all_pass_eligible(self):
        assert ex.gate_check({"hard_gates": self._gates()})["verdict"] == "ELIGIBLE"

    def test_one_fail_rejected(self):
        g = self._gates()
        g["G8_economics"] = "FAIL"
        r = ex.gate_check({"hard_gates": g})
        assert r["verdict"] == "REJECTED" and r["failed"] == ["G8_economics"]

    def test_unknown_blocked_not_passed(self):
        g = self._gates()
        g["G9_validated_demand"] = "UNKNOWN"
        r = ex.gate_check({"hard_gates": g})
        assert r["verdict"] == "BLOCKED"

    def test_reroute_tracks(self):
        r = ex.gate_check({"track": "BENCHMARK", "hard_gates": self._gates()})
        assert r["verdict"] == "REROUTE"

    def test_missing_gates_blocked(self):
        assert ex.gate_check({"hard_gates": {}})["verdict"] == "BLOCKED"

    def test_invalid_states_rejected(self):
        r = ex.gate_check({"hard_gates": {**self._gates(), "G1_installed_base": "MAYBE"}})
        assert r["verdict"] == "INVALID"


class TestCompile:
    def test_required_fields_present(self):
        spec = ex.campaign_compile({"thesis": {"thesis_id": "TH-A", "country": "NO",
                                               "atom": "pump-switch"},
                                    "evidence": {}})
        for k in ex.CAMPAIGN_REQUIRED:
            assert k in spec
        assert spec["schema_version"] == "v2"
        assert len(spec["sections"]) == 10

    def test_unknowns_explicit_tbd(self):
        spec = ex.campaign_compile({"thesis": {"thesis_id": "TH-A"}, "evidence": {}})
        assert any(str(v).startswith("TBD") for v in spec["unknowns"])
        assert "TBD:country" in spec["unknowns"]


class TestRefine:
    def test_proven_path(self):
        r = ex.refine({"campaign_id": "C-1", "tier": 3,
                       "metrics": {"resolution_success": 0.95}})
        assert r["to_state"] == "PROVEN" and r["preserved"] is True

    def test_killed_path(self):
        r = ex.refine({"campaign_id": "C-1", "tier": 0,
                       "metrics": {"kill_reason": "no demand"}})
        assert r["to_state"] == "KILLED"

    def test_mutate_middle(self):
        r = ex.refine({"campaign_id": "C-1", "tier": 2, "metrics": {}})
        assert r["to_state"] == "MUTATE"

    def test_priors_nullable(self):
        r = ex.refine({"campaign_id": "C-1", "tier": 1, "metrics": {}})
        assert set(r["priors"]) == {"supplier_success_by_class",
                                    "buyer_selector_by_component",
                                    "return_rate_by_complexity", "gap_patterns"}


class TestRunner:
    def test_full_chain(self):
        gates = {g: "PASS" for g in ex.GATES}
        out = run_chain(
            ["distill-sprawl-scan", "distill-gate-check"],
            {"inventory": [{"table": "graph_nodes", "rows": 10}],
             "candidate": {"hard_gates": gates}})
        assert len(out["receipts"]) == 2
        assert out["outputs"]["distill-gate-check"]["verdict"] == "ELIGIBLE"
        assert all(len(r["output_hash"]) == 12 for r in out["receipts"])

    def test_unknown_executor_raises(self):
        with pytest.raises(KeyError):
            run_chain(["distill-nope"], {})
