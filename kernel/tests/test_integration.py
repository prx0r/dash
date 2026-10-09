"""Integration tests — full flow through the capability gate.

Proves the complete path: agent → gate → broker → provider → result.
Agent never sees credentials. Approvals are parameter-bound.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from kernel.approvals.bind import ApprovalService
from kernel.audit.log import AuditEvent, AuditLog
from kernel.auth.identity import IdentityService
from kernel.capabilities.broker import CredentialBroker
from kernel.capabilities.gate import CapabilityGate, GateRequest, GateVerdict
from kernel.graph.schema import (
    EntityType,
    Entity,
    Edge,
    ResourceKind,
    make_company,
    make_credential_ref,
    make_integration,
    make_resource,
)
from kernel.graph.store import GraphStore
from kernel.policy.engine import Effect, PolicyEngine, PolicyRule
from kernel.tasks.schema import (
    ATask,
    HTask,
    MTask,
    TaskStatus,
    create_atask,
    create_htask,
    create_mtask,
)


def _build_full_system():
    """Build a complete system for integration testing."""
    identity = IdentityService(signing_key="integration-test-key")
    policy = PolicyEngine()
    broker = CredentialBroker()
    audit = AuditLog()
    approvals = ApprovalService(signing_key="integration-test-key")
    graph = GraphStore()

    # Register agent
    identity.register_agent(
        agent_id="cmail-agent",
        company="agentcom",
        capabilities=[
            "cloudflare.dns.read",
            "cloudflare.dns.write",
            "cloudflare.email.wire",
            "cloudflare.domain.purchase",
            "telnyx.phone.search",
            "telnyx.phone.purchase",
        ],
    )

    # Policy: specific before default deny
    policy.add_rule(PolicyRule("cloudflare", "dns.read", Effect.ALLOW))
    policy.add_rule(PolicyRule("cloudflare", "dns.write", Effect.ALLOW))
    policy.add_rule(PolicyRule("cloudflare", "email.wire", Effect.ALLOW))
    policy.add_rule(PolicyRule("cloudflare", "domain.purchase", Effect.HUMAN, budget_max=15.0))
    policy.add_rule(PolicyRule("telnyx", "phone.search", Effect.ALLOW))
    policy.add_rule(PolicyRule("telnyx", "phone.purchase", Effect.HUMAN, budget_max=10.0))
    policy.add_rule(PolicyRule("*", "*", Effect.DENY, description="default deny"))

    # Credentials
    broker.register_credential(
        vault_path="vault://agentcom/cloudflare/prod",
        provider="cloudflare",
        capabilities=["dns.read", "dns.write", "email.wire", "domain.purchase"],
        actual_value="sk_CLOUDFLARE_API_TOKEN_REAL_12345",
    )
    broker.register_credential(
        vault_path="vault://agentcom/telnyx/prod",
        provider="telnyx",
        capabilities=["phone.search", "phone.purchase"],
        actual_value="KEY_TELNYX_API_KEY_REAL_67890",
    )

    # Provider handlers
    def cloudflare_handler(action, params, credential):
        if action == "dns.read":
            return {"records": [{"type": "A", "name": params.get("name", ""), "content": "1.2.3.4"}]}
        elif action == "dns.write":
            return {"success": True, "record_id": "rec_abc123", "name": params.get("name", "")}
        elif action == "email.wire":
            return {"success": True, "zone_id": "zone_xyz", "domain": params.get("domain", "")}
        elif action == "domain.purchase":
            return {"success": True, "domain": params.get("domain", ""), "state": "active", "cost": 8.03}
        return {"error": "unknown action"}

    def telnyx_handler(action, params, credential):
        if action == "phone.search":
            return {"numbers": [{"number": "+441234567890", "monthly_cost": 1.0}]}
        elif action == "phone.purchase":
            return {"success": True, "number": params.get("number", ""), "monthly_cost": 1.5}
        return {"error": "unknown action"}

    broker.register_provider("cloudflare", cloudflare_handler)
    broker.register_provider("telnyx", telnyx_handler)

    gate = CapabilityGate(identity, policy, broker, audit)
    gate.set_approval_service(approvals)

    return gate, identity, policy, broker, audit, approvals, graph


class TestFullOnboardingFlow:
    """Test the complete Agentcom self-onboarding flow."""

    def test_domain_search_autonomous(self):
        """Agent searches for domain availability — fully autonomous."""
        gate, _, _, _, audit, _, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-001",
            capabilities=["cloudflare.dns.read"],
        )

        result = gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-001",
            company="agentcom",
            action="dns.read",
            resource_type="cloudflare",
            resource_id="agentcom.org",
            params={"name": "agentcom.org"},
        ))

        assert result.verdict == GateVerdict.ALLOW
        agent_resp = result.to_agent_response()
        assert "sk_CLOUDFLARE" not in str(agent_resp)
        assert agent_resp["data"]["records"][0]["name"] == "agentcom.org"

    def test_dns_write_autonomous(self):
        """Agent creates DNS record — fully autonomous."""
        gate, _, _, _, _, _, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-001",
            capabilities=["cloudflare.dns.write"],
        )

        result = gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-001",
            company="agentcom",
            action="dns.write",
            resource_type="cloudflare",
            resource_id="agentcom.org",
            params={"name": "mcp.agentcom.org", "type": "CNAME", "content": "cmail.tradesprior.workers.dev"},
        ))

        assert result.verdict == GateVerdict.ALLOW
        assert result.execution_result.success

    def test_domain_purchase_requires_human(self):
        """Domain purchase blocks until human approves."""
        gate, _, _, _, _, approvals, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-002",
            capabilities=["cloudflare.domain.purchase"],
        )

        # No approval → HUMAN
        result = gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-002",
            company="agentcom",
            action="domain.purchase",
            resource_type="cloudflare",
            resource_id="agentcom.org",
            params={"domain": "agentcom.org"},
            cost=8.03,
        ))

        assert result.verdict == GateVerdict.HUMAN

    def test_domain_purchase_with_approval(self):
        """Human approves → agent executes purchase."""
        gate, _, _, _, audit, approvals, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-003",
            capabilities=["cloudflare.domain.purchase"],
        )

        approval = approvals.issue(
            task_id="A-003",
            action="domain.purchase",
            resource="agentcom.org",
            provider="cloudflare",
            max_amount=15.0,
        )

        result = gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-003",
            company="agentcom",
            action="domain.purchase",
            resource_type="cloudflare",
            resource_id="agentcom.org",
            params={"domain": "agentcom.org"},
            cost=8.03,
            approval_id=approval.approval_id,
        ))

        assert result.verdict == GateVerdict.ALLOW
        assert result.execution_result.success
        # Approval consumed (single-use)
        assert approval.consumed

    def test_phone_search_autonomous(self):
        """Phone number search — autonomous."""
        gate, _, _, _, _, _, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-004",
            capabilities=["telnyx.phone.search"],
        )

        result = gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-004",
            company="agentcom",
            action="phone.search",
            resource_type="telnyx",
            resource_id="telnyx-numbers",
            params={"country": "GB"},
        ))

        assert result.verdict == GateVerdict.ALLOW
        # No Telnyx key leaked
        assert "KEY_TELNYX" not in str(result.to_agent_response())

    def test_phone_purchase_requires_human(self):
        """Phone purchase blocks until human approves."""
        gate, _, _, _, _, approvals, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-005",
            capabilities=["telnyx.phone.purchase"],
        )

        result = gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-005",
            company="agentcom",
            action="phone.purchase",
            resource_type="telnyx",
            resource_id="telnyx-number",
            params={"number": "+441234567890", "connection_id": "conn_123"},
            cost=1.5,
        ))

        assert result.verdict == GateVerdict.HUMAN


class TestCredentialIsolation:
    """Agent never sees credentials regardless of path."""

    def test_gate_response_never_contains_credential(self):
        """No matter what action, credential never appears in response."""
        gate, _, _, _, _, _, _ = _build_full_system()
        actions = [
            ("dns.read", "cloudflare", "agentcom.org"),
            ("dns.write", "cloudflare", "agentcom.org"),
            ("email.wire", "cloudflare", "agentcom.org"),
            ("phone.search", "telnyx", "telnyx-numbers"),
        ]

        for action, resource, resource_id in actions:
            token = gate._identity.issue_token(
                agent_id="cmail-agent",
                task_id="A-ISO",
                capabilities=[f"{resource}.{action}"],
            )
            result = gate.evaluate(GateRequest(
                agent_id="cmail-agent",
                token=token,
                task_id="A-ISO",
                company="agentcom",
                action=action,
                resource_type=resource,
                resource_id=resource_id,
                params={},
            ))
            response_str = str(result.to_agent_response())
            assert "sk_CLOUDFLARE_API_TOKEN_REAL_12345" not in response_str
            assert "KEY_TELNYX_API_KEY_REAL_67890" not in response_str


class TestParameterBoundApprovals:
    """Approvals are bound to specific action + resource + amount."""

    def test_approval_for_domain_a_does_not_authorize_domain_b(self):
        """Approval for agentcom.org ≠ authorization for evil.xyz."""
        gate, _, _, _, _, approvals, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-PBA",
            capabilities=["cloudflare.domain.purchase"],
        )

        approval = approvals.issue(
            task_id="A-PBA",
            action="domain.purchase",
            resource="agentcom.org",
            provider="cloudflare",
            max_amount=15.0,
        )

        # Try to buy different domain
        ok, reason = approvals.verify(
            approval,
            expected_action="domain.purchase",
            expected_resource="evil.xyz",
            cost=10.0,
        )
        assert not ok
        assert "resource mismatch" in reason

    def test_approval_for_amount_a_does_not_authorize_amount_b(self):
        """Approval for £15 ≠ authorization for £100."""
        _, _, _, _, _, approvals, _ = _build_full_system()

        approval = approvals.issue(
            task_id="A-AMT",
            action="domain.purchase",
            resource="agentcom.org",
            provider="cloudflare",
            max_amount=15.0,
        )

        ok, reason = approvals.verify(
            approval,
            expected_action="domain.purchase",
            expected_resource="agentcom.org",
            cost=100.0,
        )
        assert not ok
        assert "exceeds" in reason


class TestCompanyGraphIntegration:
    """CompanyGraph tracks all company state."""

    def test_add_company_and_resources(self):
        """Full company bootstrap tracked in graph."""
        _, _, _, _, _, _, graph = _build_full_system()

        company = make_company("agentcom", "Agentcom", country="GB")
        graph.add_entity(company)

        domain = make_resource("dom-001", "agentcom.org", ResourceKind.DOMAIN, "agentcom")
        email = make_resource("em-001", "hello@agentcom.org", ResourceKind.EMAIL, "agentcom")
        phone = make_resource("ph-001", "+441234567890", ResourceKind.PHONE, "agentcom")
        graph.add_entity(domain)
        graph.add_entity(email)
        graph.add_entity(phone)

        graph.add_edge(Edge(from_id="agentcom", to_id="dom-001", relation="owns"))
        graph.add_edge(Edge(from_id="agentcom", to_id="em-001", relation="owns"))
        graph.add_edge(Edge(from_id="agentcom", to_id="ph-001", relation="owns"))

        snapshot = graph.snapshot("agentcom")
        assert len(snapshot["entities"]) == 4
        assert len(snapshot["edges"]) == 3

    def test_credential_references_never_values(self):
        """Graph stores credential REFERENCES, never actual values."""
        _, _, _, _, _, _, graph = _build_full_system()

        cred = make_credential_ref(
            "cred-001",
            vault_path="vault://agentcom/cloudflare/prod",
            provider="cloudflare",
            capabilities=["dns.read", "dns.write"],
            company_id="agentcom",
        )
        graph.add_entity(cred)

        retrieved = graph.get("cred-001")
        assert retrieved.data["vault_path"] == "vault://agentcom/cloudflare/prod"
        assert retrieved.data["exposure_policy"] == "never"
        # The actual API key is NOT in the graph
        assert "sk_CLOUDFLARE" not in str(retrieved.data)


class TestTaskLifecycle:
    """ATask → MTask/HTask → completion."""

    def test_atask_with_mtasks_and_htasks(self):
        """Full ATask lifecycle with machine and human children."""
        atask = create_atask(
            goal="Bootstrap Agentcom identity",
            principal="owner",
            agent="cmail-agent",
            company="agentcom",
            capabilities=["cloudflare.dns.write", "cloudflare.domain.purchase"],
            budget=15.0,
            approval_policy={
                "dns.write": "autonomous",
                "domain.purchase": "human_approval",
            },
        )

        # Add MTasks (autonomous)
        m1 = create_mtask("Search domains", "name.search", {"name": "agentcom"})
        m1.status = TaskStatus.COMPLETED
        atask.mtasks.append(m1)

        m2 = create_mtask("Write DNS record", "dns.write", {"name": "mcp.agentcom.org"})
        m2.status = TaskStatus.COMPLETED
        atask.mtasks.append(m2)

        # Add HTask (human required)
        h1 = create_htask(
            "Approve domain purchase",
            reason="Financial authorization required",
            estimated_seconds=60,
            instructions="Review and approve £8.03 for agentcom.org",
        )
        atask.htasks.append(h1)

        # MTasks done, HTask pending
        assert len(atask.mtasks) == 2
        assert len(atask.htasks) == 1
        assert atask.mtasks[0].status == TaskStatus.COMPLETED
        assert atask.htasks[0].status == TaskStatus.PENDING
        assert not atask.all_completed()

        # Human completes HTask
        atask.htasks[0].status = TaskStatus.COMPLETED
        atask.htasks[0].completed_at = time.time()
        assert atask.all_completed()


class TestAuditTrailIntegration:
    """Full audit trail for all gate operations."""

    def test_complete_audit_trail(self):
        """Every operation produces a complete audit trail."""
        gate, _, _, _, audit, approvals, _ = _build_full_system()
        token = gate._identity.issue_token(
            agent_id="cmail-agent",
            task_id="A-AUDIT",
            capabilities=["cloudflare.dns.read", "cloudflare.domain.purchase"],
        )

        # 1. Autonomous action
        gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-AUDIT",
            company="agentcom",
            action="dns.read",
            resource_type="cloudflare",
            resource_id="agentcom.org",
        ))

        # 2. Human-required action (no approval)
        gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-AUDIT",
            company="agentcom",
            action="domain.purchase",
            resource_type="cloudflare",
            resource_id="agentcom.org",
            cost=8.03,
        ))

        # 3. Human-required action (with approval)
        approval = approvals.issue(
            task_id="A-AUDIT",
            action="domain.purchase",
            resource="agentcom.org",
            provider="cloudflare",
            max_amount=15.0,
        )
        gate.evaluate(GateRequest(
            agent_id="cmail-agent",
            token=token,
            task_id="A-AUDIT",
            company="agentcom",
            action="domain.purchase",
            resource_type="cloudflare",
            resource_id="agentcom.org",
            cost=8.03,
            approval_id=approval.approval_id,
        ))

        entries = audit.query(task_id="A-AUDIT")
        effects = [e.effect for e in entries]
        assert "ALLOW" in effects
        assert "HUMAN" in effects

        # Credential injections logged (without exposing value)
        injections = audit.query(event=AuditEvent.CREDENTIAL_INJECTION)
        assert len(injections) > 0
        for inj in injections:
            assert "sk_CLOUDFLARE" not in str(inj.details)
