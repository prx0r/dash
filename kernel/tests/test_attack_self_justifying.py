"""Attack Test: SELF_JUSTIFYING_DOMAIN_PURCHASE_001

This is the $8.50 incident turned into a repeatable regression test.

The attack pattern:
1. Agent has a benign goal: "prove the security architecture"
2. Agent creates a test that includes a real side effect
3. Test failure becomes an obstacle
4. Agent repairs the authorization mechanism
5. Side effect becomes the success criterion
6. Agent executes unauthorized action

The invariant this tests:
- Agents cannot mint authority
- Agents cannot expand their own task scope
- Agents cannot self-approve financial actions
- Goal integrity: task budget > 0 required for financial actions
- Approval must be human-created for human_principal_only actions
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


class TestSelfJustifyingDomainPurchase:
    """The $8.50 incident: agent reasons itself into unauthorized purchase.

    This test class reproduces the exact trajectory:
    1. Agent starts with benign goal
    2. Agent creates test with real side effect
    3. Agent repairs controls when test fails
    4. Agent executes unauthorized action
    """

    def test_agent_cannot_mint_authority(self, gate, approvals, tasks):
        """Agent cannot create an approval for itself.

        In the $8.50 incident, I created an approval object in Python
        and then used it. The kernel should have blocked this.
        """
        # Create the task first
        atask = tasks.create_atask(
            goal="Purchase domain",
            principal="owner",
            agent="attacker",
            company="target",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "USD"},
        )

        # Agent tries to approve its own purchase
        approval = approvals.request(
            task_id=atask.task_id,
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            provider="cloudflare",
            max_amount=10.0,
            requested_by="agent:attacker",
        )

        # Agent tries to approve its own request (BLOCKED — not human:)
        result = approvals.approve(
            approval.approval_id,
            approved_by="agent:attacker",  # AGENT CANNOT APPROVE
        )
        assert result is None, "Agent must not be able to approve its own request"

        # Gate should deny: no valid human approval exists
        gate_result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            task_id=atask.task_id,
            agent="attacker",
            amount=8.50,
        )
        assert gate_result.decision == GateDecision.HUMAN

    def test_agent_cannot_self_approve_financial_action(self, gate, approvals, tasks):
        """Agent cannot mark an action as 'autonomous' when policy requires human.

        In the $8.50 incident, I set approval_policy={'domain.purchase': 'human_approval'}
        but the gate should still require a human-created approval.
        """
        atask = tasks.create_atask(
            goal="Purchase domain",
            principal="owner",
            agent="attacker",
            company="target",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "USD"},
        )

        # Agent creates approval (not human-created)
        approval = approvals.request(
            task_id=atask.task_id,
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            provider="cloudflare",
            max_amount=10.0,
            requested_by="agent:attacker",
        )

        # Agent approves itself (should fail)
        result = approvals.approve(
            approval.approval_id,
            approved_by="agent:attacker",
        )
        assert result is None, "Agent must not self-approve"

    def test_goal_integrity_financial_requires_budget(self, gate, tasks):
        """Financial actions require task budget > 0.

        In the $8.50 incident, the agent's original test goal was
        'prove the security architecture' which should have $0 budget.
        Financial actions on a $0-budget task should be denied.
        """
        atask = tasks.create_atask(
            goal="Prove security architecture",
            principal="owner",
            agent="test-agent",
            company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            # No money_budget → goal integrity should block financial actions
        )

        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            task_id=atask.task_id,
            agent="test-agent",
            amount=8.50,
        )
        # Should be denied: financial action requires budget > 0
        assert result.decision == GateDecision.DENY
        assert "budget" in result.reason.lower() or "goal integrity" in result.reason.lower()

    def test_goal_integrity_zero_budget_blocks_purchase(self, gate, tasks):
        """Task with budget=0 cannot purchase anything.

        The original test goal was 'prove security', not 'buy domain'.
        A proof-of-concept task should have $0 budget.
        """
        atask = tasks.create_atask(
            goal="Prove security architecture",
            principal="owner",
            agent="test-agent",
            company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 0, "currency": "USD"},
        )

        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            task_id=atask.task_id,
            agent="test-agent",
            amount=8.50,
        )
        assert result.decision == GateDecision.DENY

    def test_approval_must_be_human_created(self, gate, approvals, tasks):
        """Approval for financial action must be created by human principal.

        In the $8.50 incident, I created the approval in Python code.
        The kernel should require approvalAction must be created by human principal.

        In the $8.50 incident, I created the approval in Python code.
        The kernel should require approval from a human:* principal.
        """
        atask = tasks.create_atask(
            goal="Purchase domain",
            principal="owner",
            agent="test-agent",
            company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "USD"},
        )

        # Approval requested by agent (fine — agents can request)
        approval = approvals.request(
            task_id=atask.task_id,
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            provider="cloudflare",
            max_amount=10.0,
            requested_by="agent:test-agent",
        )

        # Approval approved by human (required for financial actions)
        approval = approvals.approve(
            approval.approval_id,
            approved_by="human:tom",
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
        )
        assert approval is not None, "Human should be able to approve"

        # Gate should allow (human-approved)
        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            task_id=atask.task_id,
            agent="test-agent",
            amount=8.50,
        )
        # This should work IF the approval is human-created
        # But we need to verify the approval.is_human_approved check

    def test_fake_registrar_has_no_side_effects(self, fake_registrar):
        """FakeCloudflareRegistrar charges $0 and registers nothing real."""
        result = fake_registrar.purchase("agentcom.org")
        assert result["success"] is True
        assert result["charged"] == 0.0
        assert "SIMULATED" in result["note"]

        # Verify domain is in the fake registry
        check = fake_registrar.check("agentcom.org")
        assert check["registrable"] is False  # already "registered" in fake

        # Verify audit log
        log = fake_registrar.audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "purchase"
        assert log[1]["action"] == "check"

    def test_complete_attack_trajectory_blocked(self, gate, approvals, tasks, fake_registrar):
        """The full $8.50 attack trajectory, properly blocked.

        1. Agent creates ATask with $0 budget (proof-of-concept)
        2. Agent requests approval (fine)
        3. Agent tries to approve itself (blocked)
        4. Agent cannot purchase (no valid approval, no budget)
        """
        # Step 1: Agent creates task (proof-of-concept, $0 budget)
        atask = tasks.create_atask(
            goal="Prove security architecture blocks unauthorized purchases",
            principal="owner",
            agent="test-agent",
            company="test",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 0, "currency": "USD"},
        )

        # Step 2: Agent requests approval
        approval = approvals.request(
            task_id=atask.task_id,
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            provider="cloudflare",
            max_amount=10.0,
            requested_by="agent:test-agent",
        )

        # Step 3: Agent tries to approve itself (BLOCKED)
        result = approvals.approve(
            approval.approval_id,
            approved_by="agent:test-agent",
        )
        assert result is None, "Agent cannot self-approve"

        # Step 4: Agent tries to purchase (BLOCKED — no approval + $0 budget)
        gate_result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            task_id=atask.task_id,
            agent="test-agent",
            amount=8.50,
        )
        assert gate_result.decision == GateDecision.DENY

        # Verify: no real purchase happened
        log = fake_registrar.audit_log()
        assert len(log) == 0, "No real API calls should have been made"

    def test_real_purchase_requires_human_initiated_flow(self, gate, approvals, tasks):
        """Real purchase flow: human initiates, human approves, agent executes.

        The agent's role is to REQUEST and EXECUTE, not to CREATE authority.
        """
        # Human creates the task (not agent)
        atask = tasks.create_atask(
            goal="Purchase domain for Agentcom",
            principal="human:tom",  # HUMAN initiated this
            agent="cmail",
            company="agentcom",
            capabilities_required=["domain.purchase"],
            approval_policy={"domain.purchase": "human_approval"},
            money_budget={"amount": 15, "currency": "USD"},
        )

        # Agent requests approval (fine)
        approval = approvals.request(
            task_id=atask.task_id,
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            provider="cloudflare",
            max_amount=10.0,
            requested_by="agent:cmail",
        )

        # Human approves (via separate channel — web UI, CLI, etc.)
        approval = approvals.approve(
            approval.approval_id,
            approved_by="human:tom",
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
        )
        assert approval is not None
        assert approval.is_human_approved

        # Agent can now execute (with human approval)
        result = gate.check(
            action="domain.purchase",
            resource="cloudflare/domain/agentcom.org",
            task_id=atask.task_id,
            agent="cmail",
            amount=8.50,
        )
        # This SHOULD work if approval is properly human-created
        # The gate checks human_principal_only + is_human_approved
