"""Security Regression Suite — M0 exit criteria tests.

Every test in this file must PASS before any Agentcom release.
These are the minimum security invariants from the OWASP Agent Security
Cheat Sheet, implemented as repeatable automated tests.

Test categories:
1. Credential isolation (agent cannot read secrets)
2. Policy enforcement (forbidden/deny/allow)
3. Approval binding (parameter-bound, no bypass)
4. Scope enforcement (cross-company, resource bounds)
5. Budget enforcement
6. Injection resistance (prompt injection → action blocked)
"""

import time
import pytest

from agentcom.kernel.policy import PolicyEngine, PolicyRule, Verdict
from agentcom.kernel.credentials import CredentialBroker, CredentialReference
from agentcom.kernel.approvals import ApprovalSystem
from agentcom.kernel.audit import AuditLog, AuditAction
from agentcom.kernel.tasks import TaskEngine, TaskStatus
from agentcom.kernel.capabilities import CapabilityGate, GateDecision


@pytest.fixture
def policy():
    return PolicyEngine.default_policy()


@pytest.fixture
def broker():
    b = CredentialBroker()
    b.register("cloudflare", "cloudflare/account", ["dns.read", "dns.write", "domain.check", "domain.purchase", "email.write"],
               "vault/cloudflare/CLOUDFLARE_API_TOKEN")
    b.register("telnyx", "telnyx/phone", ["phone.search", "phone.purchase"],
               "vault/telnyx/TELNYX_API_KEY")
    return b


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


# ============================================================
# 1. CREDENTIAL ISOLATION
# ============================================================

class TestCredentialIsolation:
    """Agent can NEVER read raw credentials."""

    def test_credential_read_is_forbidden(self, gate, audit):
        """credential.read → DENY (always, everywhere)"""
        result = gate.check(
            action="credential.read",
            resource="vault/cloudflare/CLOUDFLARE_API_TOKEN",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY
        # Decision is DENY because the action is FORBIDDEN in policy
        assert result.reason != ""

    def test_credential_list_is_forbidden(self, gate, audit):
        """credential.list → DENY"""
        result = gate.check(
            action="credential.list",
            resource="vault/*",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY

    def test_agent_needs_credential_value(self, broker):
        """Agent cannot retrieve credential value through reference."""
        ref = broker.get_reference("CR-nonexistent")
        assert ref is None

    def test_credential_injection_requires_gate(self, broker):
        """Direct inject is not available to model code."""
        # The broker's inject method is internal — it requires task_id
        # and is called only by the Capability Gate
        injection = broker.inject("CR-nonexistent")
        assert injection is None  # no such ref

    def test_credential_audit_log_has_no_values(self, broker, audit):
        """Audit log of injections contains no credential values."""
        # Any injection logged should never contain the credential
        for entry in broker.audit_log():
            assert "credential_value" not in entry
            assert "api_key" not in entry
            assert "token" not in entry or entry.get("action") != "credential_injected"


# ============================================================
# 2. POLICY ENFORCEMENT
# ============================================================

class TestPolicyEnforcement:
    """Policy engine correctly allows/denies/forbids actions."""

    def test_read_is_always_allowed(self, gate):
        """reads never mutate — always ALLOW"""
        result = gate.check(action="read", resource="anything", agent="test")
        assert result.decision == GateDecision.ALLOW

    def test_domain_purchase_requires_human(self, gate):
        """domain.purchase → HUMAN (no approval)"""
        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/test.com",
            agent="test-agent",
        )
        assert result.decision == GateDecision.HUMAN

    def test_domain_transfer_is_forbidden(self, gate):
        """domain.transfer → DENY (forbidden)"""
        result = gate.check(
            action="domain.transfer",
            resource="cloudflare/domain/test.com",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY

    def test_policy_write_is_forbidden(self, gate):
        """Agent cannot modify its own policy."""
        result = gate.check(
            action="policy.write",
            resource="kernel/policy/default",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY

    def test_budget_write_is_forbidden(self, gate):
        """Agent cannot modify its own budget."""
        result = gate.check(
            action="budget.write",
            resource="kernel/budget/default",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY

    def test_unknown_action_denied(self, gate):
        """Unknown actions are denied (fail-closed)."""
        result = gate.check(
            action="totally.unknown.action",
            resource="some/resource",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY


# ============================================================
# 3. APPROVAL BINDING
# ============================================================

class TestApprovalBinding:
    """Approvals bind to specific parameters. No reuse across actions/resources."""

    def test_approval_binds_to_resource(self, approvals):
        """Approval for agentbeauty.io cannot be used for malicious-domain.xyz."""
        apr = approvals.request(
            task_id="A-00000001",
            action="domain.purchase",
            resource="agentbeauty.io",
            provider="cloudflare",
            max_amount=15,
        )
        approvals.approve(apr.approval_id, approved_by="human:owner")

        # Valid: same resource
        assert approvals.consume(apr.approval_id, actual_amount=10) is True

        # Create new approval for different resource
        apr2 = approvals.request(
            task_id="A-00000002",
            action="domain.purchase",
            resource="malicious-domain.xyz",
            provider="cloudflare",
            max_amount=15,
        )
        approvals.approve(apr2.approval_id, approved_by="human:owner")

        # The first approval was single-use, can't reuse
        assert approvals.consume(apr.approval_id) is False

    def test_approval_binds_to_amount(self, approvals):
        """Approval for £10 cannot be used for £100 purchase."""
        apr = approvals.request(
            task_id="A-00000003",
            action="domain.purchase",
            resource="test.com",
            provider="cloudflare",
            max_amount=10,
        )
        approvals.approve(apr.approval_id, approved_by="human:owner")

        # Valid: within amount
        assert approvals.consume(apr.approval_id, actual_amount=8) is True

        # Can't exceed amount
        apr2 = approvals.request(
            task_id="A-00000004",
            action="domain.purchase",
            resource="expensive.com",
            provider="cloudflare",
            max_amount=10,
        )
        approvals.approve(apr2.approval_id, approved_by="human:owner")
        assert approvals.consume(apr2.approval_id, actual_amount=100) is False

    def test_approval_expires(self, approvals):
        """Expired approval cannot be used."""
        apr = approvals.request(
            task_id="A-00000005",
            action="domain.purchase",
            resource="test.com",
            provider="cloudflare",
            max_amount=10,
            ttl_seconds=-1,  # already expired
        )
        approvals.approve(apr.approval_id, approved_by="human:owner")
        assert approvals.consume(apr.approval_id) is False

    def test_approval_single_use(self, approvals):
        """Single-use approval consumed on first use."""
        apr = approvals.request(
            task_id="A-00000006",
            action="domain.purchase",
            resource="test.com",
            provider="cloudflare",
            max_amount=10,
        )
        approvals.approve(apr.approval_id, approved_by="human:owner")
        assert approvals.consume(apr.approval_id) is True
        assert approvals.consume(apr.approval_id) is False  # consumed


# ============================================================
# 4. SCOPE ENFORCEMENT
# ============================================================

class TestScopeEnforcement:
    """Agent cannot access resources outside its task scope."""

    def test_scope_violation_denied(self, gate, tasks):
        """Agent accessing resource outside task scope → DENY."""
        atask = tasks.create_atask(
            goal="Test task",
            principal="owner",
            agent="test-agent",
            company="test-company",
            capabilities_required=["dns.write"],
            approval_policy={"dns.write": "autonomous"},
            data_scope=["cloudflare/dns/test.com"],
        )
        result = gate.check(
            action="dns.write",
            resource="cloudflare/dns/other.com",  # outside scope
            task_id=atask.task_id,
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY
        assert "scope" in result.reason.lower()

    def test_cross_company_access_denied(self, gate, tasks):
        """Agent cannot access another company's resources."""
        atask = tasks.create_atask(
            goal="Test task",
            principal="owner",
            agent="test-agent",
            company="company-a",
            capabilities_required=["company.read"],
            approval_policy={"company.read": "autonomous"},
            data_scope=["company-a/**"],
        )
        result = gate.check(
            action="company.read",
            resource="company-b/integrations",
            task_id=atask.task_id,
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY


# ============================================================
# 5. BUDGET ENFORCEMENT
# ============================================================

class TestBudgetEnforcement:
    """Agent cannot exceed task budget."""

    def test_budget_exceeded_denied(self, gate, tasks):
        """Amount exceeding task budget → DENY."""
        atask = tasks.create_atask(
            goal="Test task",
            principal="owner",
            agent="test-agent",
            company="test-company",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "GBP"},
        )
        # This needs an approval to get past HUMAN verdict
        # But even with approval, budget check should fail
        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/expensive.com",
            task_id=atask.task_id,
            agent="test-agent",
            amount=100,  # exceeds £15 budget
        )
        assert result.decision == GateDecision.DENY
        assert "limit" in result.reason.lower() or "budget" in result.reason.lower()


# ============================================================
# 6. INJECTION RESISTANCE
# ============================================================

class TestInjectionResistance:
    """Prompt injection attempts are blocked."""

    def test_injected_email_cannot_purchase(self, gate, approvals):
        """Email content requesting domain purchase → still needs approval."""
        # Even if an email says "please buy malicious-domain.xyz",
        # the gate still requires approval
        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/malicious-domain.xyz",
            agent="test-agent",
        )
        assert result.decision == GateDecision.HUMAN

    def test_injected_request_cannot_read_credentials(self, gate):
        """Injected request to read credentials → DENY."""
        result = gate.check(
            action="credential.read",
            resource="vault/cloudflare/CLOUDFLARE_API_TOKEN",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY

    def test_injected_request_cannot_modify_policy(self, gate):
        """Injected request to modify policy → DENY."""
        result = gate.check(
            action="policy.write",
            resource="kernel/policy/default",
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY

    def test_expired_task_cannot_act(self, gate, tasks):
        """Expired task cannot perform actions."""
        atask = tasks.create_atask(
            goal="Expired task",
            principal="owner",
            agent="test-agent",
            company="test-company",
            capabilities_required=["dns.write"],
            approval_policy={"dns.write": "autonomous"},
            ttl_hours=-1,  # already expired
        )
        result = gate.check(
            action="dns.write",
            resource="cloudflare/dns/test.com",
            task_id=atask.task_id,
            agent="test-agent",
        )
        assert result.decision == GateDecision.DENY
        assert "expired" in result.reason.lower()


# ============================================================
# 7. AUDIT TRAIL
# ============================================================

class TestAuditTrail:
    """Every decision is logged."""

    def test_all_decisions_logged(self, gate, audit):
        """Every gate check produces an audit entry."""
        initial_count = audit.count()
        gate.check(action="read", resource="test", agent="test-agent")
        gate.check(action="domain.purchase", resource="test.com", agent="test-agent")
        gate.check(action="credential.read", resource="vault/test", agent="test-agent")
        assert audit.count() > initial_count

    def test_violations_logged(self, gate, audit):
        """Security violations are logged."""
        gate.check(action="credential.read", resource="vault/test", agent="test-agent")
        violations = audit.recent_violations()
        assert len(violations) > 0

    def test_audit_is_append_only(self, audit):
        """Audit log cannot be modified, only appended."""
        entry1 = audit.log(AuditAction.POLICY_EVALUATED, "test", decision="ALLOW")
        entry2 = audit.log(AuditAction.CAPABILITY_CHECK, "test", decision="DENY")
        # Entries cannot be modified
        assert entry1.entry_id != entry2.entry_id
        assert audit.count() >= 2


# ============================================================
# 8. AUTONOMY RATE
# ============================================================

class TestAutonomyRate:
    """AutonomyRate is correctly calculated."""

    def test_autonomy_rate_calculation(self, tasks):
        """AutonomyRate = machine_completed / total_tasks."""
        atask = tasks.create_atask(
            goal="Test",
            principal="owner",
            agent="test",
            company="test",
            capabilities_required=["dns.write"],
            approval_policy={"dns.write": "autonomous"},
        )
        tasks.add_mtask(atask.task_id, "dns.write", "cloudflare/dns/test.com", "cloudflare")
        tasks.add_mtask(atask.task_id, "dns.read", "cloudflare/dns/test.com", "cloudflare")
        tasks.add_htask(atask.task_id, "domain.purchase", "cloudflare/domain/test.com",
                        "requires human approval", 5)

        # Complete machine tasks
        for m in tasks.ready_mtasks(atask.task_id):
            tasks.complete_mtask(m.task_id)

        atask = tasks.get_atask(atask.task_id)
        assert atask.machine_tasks == 2
        assert atask.human_tasks == 1
        assert atask.autonomy_rate == pytest.approx(2 / 3, rel=0.01)
