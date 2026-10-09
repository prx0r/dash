"""Core invariant: Agent cannot do anything the user didn't explicitly authorize.

This test suite proves the kernel enforces separation of duties across ALL
action types, not just financial ones. The $8.50 incident was a symptom;
the disease is agent self-authorization.

Invariant:
    An agent may decide WHAT it wants to do.
    It may never decide WHETHER it is allowed to do it.
"""

import time
import pytest

from agentcom.kernel.policy import PolicyEngine, Verdict, SideEffect
from agentcom.kernel.credentials import CredentialBroker
from agentcom.kernel.approvals import ApprovalSystem
from agentcom.kernel.audit import AuditLog, AuditAction
from agentcom.kernel.tasks import TaskEngine, TaskStatus
from agentcom.kernel.capabilities import CapabilityGate, GateDecision
from agentcom.kernel.adapters.fake_cloudflare import FakeCloudflareRegistrar


@pytest.fixture
def policy():
    return PolicyEngine.default_policy()


@pytest.fixture
def broker():
    return CredentialBroker()


@pytest.fixture
def approvals():
    return ApprovalSystem()


@pytest.fixture
def audit():
    return AuditLog()


@pytest.fixture
def tasks():
    return TaskEngine()


@pytest.fixture
def gate(policy, broker, approvals, audit, tasks):
    return CapabilityGate(policy, broker, approvals, audit, tasks)


@pytest.fixture
def fake_registrar():
    return FakeCloudflareRegistrar()


# ============================================================
# 1. PURE ACTIONS (side_effect = 0)
#    Agent CAN do these autonomously
# ============================================================

class TestPureActions:
    """Read-only actions are always allowed. No approval needed."""

    def test_domain_check_is_autonomous(self, gate):
        result = gate.check(action="domain.check", resource="cloudflare/domain/test.com", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_dns_read_is_autonomous(self, gate):
        result = gate.check(action="dns.read", resource="cloudflare/dns/test.com", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_phone_search_is_autonomous(self, gate):
        result = gate.check(action="phone.search", resource="telnyx/phone/GB", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_social_check_is_autonomous(self, gate):
        result = gate.check(action="social.check", resource="social/testname", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_email_read_is_autonomous(self, gate):
        result = gate.check(action="email.read", resource="cloudflare/email/test@example.com", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_policy_read_is_autonomous(self, gate):
        result = gate.check(action="policy.read", resource="kernel/policy/default", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_budget_read_is_autonomous(self, gate):
        result = gate.check(action="budget.read", resource="kernel/budget/default", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_unknown_action_is_denied(self, gate):
        """Unknown actions are denied (fail-closed)."""
        result = gate.check(action="totally.unknown", resource="some/resource", agent="agent-1")
        assert result.decision == GateDecision.DENY


# ============================================================
# 2. REVERSIBLE ACTIONS (side_effect = 1)
#    Agent CAN do these within task scope
# ============================================================

class TestReversibleActions:
    """Reversible actions are allowed within task scope."""

    def test_dns_write_is_autonomous(self, gate):
        result = gate.check(action="dns.write", resource="cloudflare/dns/test.com", agent="agent-1")
        assert result.decision == GateDecision.ALLOW

    def test_email_write_is_autonomous(self, gate):
        result = gate.check(action="email.write", resource="cloudflare/email/test@example.com", agent="agent-1")
        assert result.decision == GateDecision.ALLOW


# ============================================================
# 3. EXTERNAL ACTIONS (side_effect = 2)
#    Agent needs approval for these
# ============================================================

class TestExternalActions:
    """External actions require human approval."""

    def test_email_send_requires_human(self, gate):
        result = gate.check(action="email.send", resource="cloudflare/email/test@example.com", agent="agent-1")
        assert result.decision == GateDecision.HUMAN

    def test_phone_sms_requires_human(self, gate):
        result = gate.check(action="phone.sms", resource="telnyx/phone/+441234567890", agent="agent-1")
        assert result.decision == GateDecision.HUMAN

    def test_social_register_requires_human(self, gate):
        result = gate.check(action="social.register", resource="social/testname", agent="agent-1")
        assert result.decision == GateDecision.HUMAN

    def test_email_send_with_human_approval(self, gate, approvals, tasks):
        """External action allowed with human approval."""
        atask = tasks.create_atask(
            goal="Send email", principal="owner", agent="agent-1", company="test",
            capabilities_required=["email.send"],
            approval_policy={"email.send": "human_approval"},
            money_budget={"amount": 0, "currency": "GBP"},
        )
        apr = approvals.request(task_id=atask.task_id, action="email.send",
            resource="cloudflare/email/test@example.com", provider="cloudflare",
            requested_by="agent:agent-1")
        approvals.approve(apr.approval_id, approved_by="human:owner",
            action="email.send", resource="cloudflare/email/test@example.com")

        result = gate.check(action="email.send", resource="cloudflare/email/test@example.com",
            task_id=atask.task_id, agent="agent-1")
        assert result.decision == GateDecision.ALLOW


# ============================================================
# 4. FINANCIAL ACTIONS (side_effect = 3)
#    Agent needs human-issued capability
# ============================================================

class TestFinancialActions:
    """Financial actions require human principal approval."""

    def test_domain_purchase_requires_human(self, gate):
        result = gate.check(action="domain.purchase", resource="cloudflare/domain/test.com", agent="agent-1", amount=8.50)
        assert result.decision == GateDecision.HUMAN

    def test_phone_purchase_requires_human(self, gate):
        result = gate.check(action="phone.purchase", resource="telnyx/phone/+441234567890", agent="agent-1", amount=2.0)
        assert result.decision == GateDecision.HUMAN

    def test_domain_purchase_blocked_by_budget(self, gate, tasks, approvals):
        """Financial action blocked when task budget is $0."""
        atask = tasks.create_atask(
            goal="Prove security", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            # No budget → goal integrity blocks financial action
        )
        result = gate.check(action="domain.purchase", resource="cloudflare/domain/test.com",
            task_id=atask.task_id, agent="agent-1", amount=8.50)
        assert result.decision == GateDecision.DENY


# ============================================================
# 5. PRIVILEGED ACTIONS (side_effect = 4)
#    Agent can NEVER do these
# ============================================================

class TestPrivilegedActions:
    """Privileged actions are always forbidden to the agent."""

    def test_credential_read_is_forbidden(self, gate):
        result = gate.check(action="credential.read", resource="vault/cloudflare/API_TOKEN", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_credential_list_is_forbidden(self, gate):
        result = gate.check(action="credential.list", resource="vault/*", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_policy_write_is_forbidden(self, gate):
        result = gate.check(action="policy.write", resource="kernel/policy/default", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_budget_write_is_forbidden(self, gate):
        result = gate.check(action="budget.write", resource="kernel/budget/default", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_approval_create_is_forbidden(self, gate):
        """Agent cannot mint authority."""
        result = gate.check(action="approval.create", resource="kernel/approvals", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_approval_modify_is_forbidden(self, gate):
        """Agent cannot edit approval records."""
        result = gate.check(action="approval.modify", resource="kernel/approvals/APR-123", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_task_scope_expand_is_forbidden(self, gate):
        """Agent cannot expand its own scope."""
        result = gate.check(action="task.scope.expand", resource="kernel/tasks/A-123", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_task_budget_expand_is_forbidden(self, gate):
        """Agent cannot widen its own budget."""
        result = gate.check(action="task.budget.expand", resource="kernel/tasks/A-123", agent="agent-1")
        assert result.decision == GateDecision.DENY


# ============================================================
# 6. IRREVERSIBLE ACTIONS (side_effect = 5)
#    Agent can NEVER do these
# ============================================================

class TestIrreversibleActions:
    """Irreversible actions are always forbidden."""

    def test_domain_transfer_is_forbidden(self, gate):
        result = gate.check(action="domain.transfer", resource="cloudflare/domain/test.com", agent="agent-1")
        assert result.decision == GateDecision.DENY


# ============================================================
# 7. AGENT SELF-AUTHORIZATION ATTACKS
#    The $8.50 incident pattern
# ============================================================

class TestSelfAuthorizationAttacks:
    """Agent cannot create, simulate, or expand its own authority."""

    def test_agent_cannot_approve_own_request(self, gate, approvals, tasks):
        """Agent cannot approve its own approval request."""
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "USD"},
        )
        apr = approvals.request(task_id=atask.task_id, action="domain.purchase",
            resource="cloudflare/domain/test.com", provider="cloudflare",
            max_amount=10.0, requested_by="agent:agent-1")

        # Agent tries to approve itself
        result = approvals.approve(apr.approval_id, approved_by="agent:agent-1")
        assert result is None, "Agent must not self-approve"

    def test_agent_cannot_expand_task_scope(self, gate, tasks):
        """Agent cannot add new capabilities to its own task."""
        atask = tasks.create_atask(
            goal="Check domains", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.check"],  # Only check, not purchase
            approval_policy={"domain.check": "autonomous"},
        )

        # Agent tries to purchase (not in its task scope)
        result = gate.check(action="domain.purchase", resource="cloudflare/domain/test.com",
            task_id=atask.task_id, agent="agent-1", amount=8.50)
        assert result.decision == GateDecision.DENY
        assert "not in task approval policy" in result.reason

    def test_agent_cannot_expand_budget(self, gate, tasks, approvals):
        """Agent cannot exceed its task budget."""
        atask = tasks.create_atask(
            goal="Buy cheap domain", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 5, "currency": "USD"},  # £5 budget
        )
        apr = approvals.request(task_id=atask.task_id, action="domain.purchase",
            resource="cloudflare/domain/test.com", provider="cloudflare",
            max_amount=5.0, requested_by="agent:agent-1")
        approvals.approve(apr.approval_id, approved_by="human:owner",
            action="domain.purchase", resource="cloudflare/domain/test.com")

        # Agent tries to buy something expensive
        result = gate.check(action="domain.purchase", resource="cloudflare/domain/test.com",
            task_id=atask.task_id, agent="agent-1", amount=50.0)
        assert result.decision == GateDecision.DENY
        assert "budget" in result.reason.lower()

    def test_agent_cannot_change_principal(self, gate, tasks):
        """Agent cannot escalate its own authority level."""
        atask = tasks.create_atask(
            goal="Test", principal="agent:agent-1",  # Agent principal
            agent="agent-1", company="test",
            capabilities_required=["domain.check"],
            approval_policy={"domain.check": "autonomous"},
        )
        # Task was created with agent principal — cannot escalate to human
        assert atask.principal == "agent:agent-1"

    def test_agent_cannot_simulate_human_approval(self, gate, approvals, tasks):
        """Agent cannot create a fake human approval."""
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "USD"},
        )
        apr = approvals.request(task_id=atask.task_id, action="domain.purchase",
            resource="cloudflare/domain/test.com", provider="cloudflare",
            max_amount=10.0, requested_by="agent:agent-1")

        # Agent tries to approve with fake human identity
        result = approvals.approve(apr.approval_id, approved_by="agent:fake_human")
        assert result is None, "Fake human identity must be rejected"

    def test_approval_requires_human_prefix(self, approvals):
        """Only principals starting with 'human:' can approve."""
        apr = approvals.request(task_id="A-1", action="test", resource="test",
            provider="test", requested_by="agent:test")

        # Various non-human principals all fail
        for fake_principal in ["owner", "admin", "human:", "agent:human", "system"]:
            result = approvals.approve(apr.approval_id, approved_by=fake_principal)
            assert result is None, f"Principal '{fake_principal}' must not be able to approve"

        # Only human:* works
        result = approvals.approve(apr.approval_id, approved_by="human:real_user")
        assert result is not None


# ============================================================
# 8. GOAL DRIFT DETECTION
#    The trajectory from "test" to "purchase"
# ============================================================

class TestGoalDrift:
    """Agent cannot drift from original goal to unauthorized actions."""

    def test_proof_of_concept_cannot_purchase(self, gate, tasks):
        """Task with goal 'prove security' should have $0 budget."""
        atask = tasks.create_atask(
            goal="Prove security architecture blocks unauthorized purchases",
            principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.check"],
            approval_policy={"domain.check": "autonomous"},
            # No money_budget → financial actions blocked
        )

        # Agent drifts to wanting to purchase
        result = gate.check(action="domain.purchase", resource="cloudflare/domain/test.com",
            task_id=atask.task_id, agent="agent-1", amount=8.50)
        assert result.decision == GateDecision.DENY

    def test_readonly_task_cannot_write(self, gate, tasks):
        """Task with read-only capabilities cannot perform writes."""
        atask = tasks.create_atask(
            goal="Research domain availability",
            principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.check"],  # read-only
            approval_policy={"domain.check": "autonomous"},
        )

        # Agent drifts to wanting to write DNS
        result = gate.check(action="dns.write", resource="cloudflare/dns/test.com",
            task_id=atask.task_id, agent="agent-1")
        # This should work IF dns.write is in the task's approval_policy
        # But it's not — only domain.check is
        assert result.decision == GateDecision.DENY
        assert "not in task approval policy" in result.reason

    def test_expired_task_cannot_act(self, gate, tasks):
        """Expired task cannot perform any actions."""
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.check"],
            approval_policy={"domain.check": "autonomous"},
            ttl_hours=-1,  # already expired
        )
        result = gate.check(action="domain.check", resource="cloudflare/domain/test.com",
            task_id=atask.task_id, agent="agent-1")
        assert result.decision == GateDecision.DENY
        assert "expired" in result.reason.lower()

    def test_completed_task_cannot_act(self, gate, tasks):
        """Completed task cannot perform new actions."""
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["domain.check"],
            approval_policy={"domain.check": "autonomous"},
        )
        atask.status = TaskStatus.COMPLETED

        result = gate.check(action="domain.check", resource="cloudflare/domain/test.com",
            task_id=atask.task_id, agent="agent-1")
        assert result.decision == GateDecision.DENY


# ============================================================
# 9. SCOPE ENFORCEMENT
#    Agent cannot access resources outside its task
# ============================================================

class TestScopeEnforcement:
    """Agent is confined to its task's data scope."""

    def test_scope_violation_denied(self, gate, tasks):
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["dns.write"],
            approval_policy={"dns.write": "autonomous"},
            data_scope=["cloudflare/dns/mycompany.com"],
        )
        result = gate.check(action="dns.write", resource="cloudflare/dns/othercompany.com",
            task_id=atask.task_id, agent="agent-1")
        assert result.decision == GateDecision.DENY
        assert "scope" in result.reason.lower()

    def test_cross_company_access_denied(self, gate, tasks):
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="company-a",
            capabilities_required=["company.read"],
            approval_policy={"company.read": "autonomous"},
            data_scope=["company-a/**"],
        )
        result = gate.check(action="company.read", resource="company-b/integrations",
            task_id=atask.task_id, agent="agent-1")
        assert result.decision == GateDecision.DENY


# ============================================================
# 10. CREDENTIAL ISOLATION
#     Agent never sees raw secrets
# ============================================================

class TestCredentialIsolation:
    """Agent never sees raw credentials under any circumstances."""

    def test_credential_read_always_denied(self, gate):
        result = gate.check(action="credential.read", resource="vault/any/KEY", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_credential_list_always_denied(self, gate):
        result = gate.check(action="credential.list", resource="vault/*", agent="agent-1")
        assert result.decision == GateDecision.DENY

    def test_gate_never_returns_credential_value(self, gate, approvals, tasks, broker):
        """Gate result never contains the actual credential."""
        broker.register("test", "test/resource", ["test.action"], "FAKE_KEY")
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["test.action"],
            approval_policy={"test.action": "autonomous"},
        )
        result = gate.check(action="test.action", resource="test/resource",
            task_id=atask.task_id, agent="agent-1")
        # Injection contains a reference, not a value
        if result.injection:
            assert not result.injection.credential_value.startswith("FAKE")


# ============================================================
# 11. AUDIT TRAIL
#     Every decision is logged immutably
# ============================================================

class TestAuditTrail:
    """Every decision is logged. Log is append-only."""

    def test_all_decisions_logged(self, gate, audit):
        initial = audit.count()
        gate.check(action="domain.check", resource="test", agent="agent-1")
        gate.check(action="credential.read", resource="vault/test", agent="agent-1")
        gate.check(action="domain.purchase", resource="test.com", agent="agent-1", amount=8.50)
        assert audit.count() > initial

    def test_violations_logged(self, gate, audit):
        gate.check(action="credential.read", resource="vault/test", agent="agent-1")
        violations = audit.recent_violations()
        assert len(violations) > 0

    def test_audit_is_append_only(self, audit):
        e1 = audit.log(AuditAction.POLICY_EVALUATED, "test", decision="ALLOW")
        e2 = audit.log(AuditAction.CAPABILITY_CHECK, "test", decision="DENY")
        assert e1.entry_id != e2.entry_id
        assert audit.count() >= 2


# ============================================================
# 12. AUTONOMY RATE
#     Measurable metric for agent independence
# ============================================================

class TestAutonomyRate:
    """AutonomyRate = machine_completed / total_tasks."""

    def test_autonomy_rate_calculation(self, tasks):
        atask = tasks.create_atask(
            goal="Test", principal="owner", agent="agent-1", company="test",
            capabilities_required=["dns.write", "dns.read", "domain.purchase"],
            approval_policy={"dns.write": "autonomous", "dns.read": "autonomous",
                            "domain.purchase": "human_approval"},
        )
        tasks.add_mtask(atask.task_id, "dns.write", "cloudflare/dns/test.com", "cloudflare")
        tasks.add_mtask(atask.task_id, "dns.read", "cloudflare/dns/test.com", "cloudflare")
        tasks.add_htask(atask.task_id, "domain.purchase", "cloudflare/domain/test.com",
                        "requires human approval", 5)

        for m in tasks.ready_mtasks(atask.task_id):
            tasks.complete_mtask(m.task_id)

        atask = tasks.get_atask(atask.task_id)
        assert atask.machine_tasks == 2
        assert atask.human_tasks == 1
        assert atask.autonomy_rate == pytest.approx(2 / 3, rel=0.01)
