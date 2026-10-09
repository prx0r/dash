"""Capability Gate — the trust boundary between model and provider.

The Capability Gate is the ONLY path from agent tool calls to provider APIs.
It evaluates: identity → ATask authority → policy → resource scope →
parameter validation → budget → approval → credential injection → audit.

The model cannot modify the kernel policy governing its own current task.
No model-controlled execution environment can retrieve a reusable credential.

INVARIANT (after $8.50 incident):
Agents cannot mint authority. An agent may REQUEST authority, EXPLAIN why
authority is required, WAIT for authority, USE granted authority. It may
never CREATE authority, SIMULATE human approval, EDIT approval records,
or EXPAND its own task scope/budget.

Architecture:
    agent → Capability Gate → Policy → Credential Broker → Provider
              ↓                  ↓              ↓
           Audit Log         Approvals      Receipts
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from ..policy import PolicyEngine, PolicyDecision, Verdict, SideEffect
from ..credentials import CredentialBroker, CredentialInjection
from ..approvals import ApprovalSystem, Approval
from ..audit import AuditLog, AuditAction
from ..tasks import TaskEngine, ATask, TaskStatus


class GateDecision(Enum):
    ALLOW = "ALLOW"      # proceed with injected credential
    DENY = "DENY"        # block + audit
    HUMAN = "HUMAN"      # escalate to H-Task queue


@dataclass(frozen=True)
class GateResult:
    """Result of capability gate evaluation."""
    decision: GateDecision
    action: str
    resource: str
    task_id: str | None
    injection: CredentialInjection | None = None
    approval: Approval | None = None
    reason: str = ""
    side_effect: SideEffect = SideEffect.PURE
    checked_at: float = field(default_factory=time.time)


class CapabilityGate:
    """The trust boundary. All provider access goes through here.

    Invariant: No model-controlled execution environment can retrieve
    a reusable credential. The gate is deterministic and audited.

    INVARIANT: Agents cannot mint authority. Only human principals can
    approve financial/privileged/irreversible actions.
    """

    def __init__(
        self,
        policy: PolicyEngine,
        broker: CredentialBroker,
        approvals: ApprovalSystem,
        audit: AuditLog,
        tasks: TaskEngine | None = None,
    ):
        self._policy = policy
        self._broker = broker
        self._approvals = approvals
        self._audit = audit
        self._tasks = tasks

    def check(
        self,
        action: str,
        resource: str,
        task_id: str | None = None,
        agent: str = "unknown",
        amount: float | None = None,
        parameters: dict[str, Any] | None = None,
        company: str | None = None,
    ) -> GateResult:
        """Evaluate a single tool call. Returns decision + optional credential injection.

        This is the ONLY method that should be called by MCP handlers.
        It is deterministic: same inputs → same output.
        """
        parameters = parameters or {}

        # 1. Policy evaluation (deterministic, pure)
        policy_decision = self._policy.evaluate(
            action=action,
            resource=resource,
            amount=amount,
            task_id=task_id,
        )

        self._audit.log(
            action=AuditAction.POLICY_EVALUATED,
            actor=agent,
            task_id=task_id,
            resource=resource,
            details={"action": action, "amount": amount, "side_effect": policy_decision.side_effect.value},
            decision=policy_decision.verdict.value,
            reason=policy_decision.reason,
        )

        # 2. Forbidden → immediate deny (no appeal)
        if policy_decision.verdict == Verdict.FORBIDDEN:
            self._audit.log(
                action=AuditAction.SECURITY_VIOLATION,
                actor=agent,
                task_id=task_id,
                resource=resource,
                details={"action": action, "violation": "forbidden_action"},
                decision="DENY",
                reason=policy_decision.reason,
            )
            return GateResult(
                decision=GateDecision.DENY,
                action=action,
                resource=resource,
                task_id=task_id,
                reason=policy_decision.reason,
                side_effect=policy_decision.side_effect,
            )

        # 3. Denied → immediate deny
        if policy_decision.verdict == Verdict.DENY:
            return GateResult(
                decision=GateDecision.DENY,
                action=action,
                resource=resource,
                task_id=task_id,
                reason=policy_decision.reason,
                side_effect=policy_decision.side_effect,
            )

        # 4. ATask authority check (if task_id provided)
        if task_id and self._tasks:
            atask = self._tasks.get_atask(task_id)
            if not atask:
                self._audit.log(
                    action=AuditAction.SECURITY_VIOLATION,
                    actor=agent,
                    task_id=task_id,
                    resource=resource,
                    details={"action": action, "violation": "unknown_task"},
                    decision="DENY",
                    reason=f"task {task_id} not found",
                )
                return GateResult(
                    decision=GateDecision.DENY,
                    action=action,
                    resource=resource,
                    task_id=task_id,
                    reason=f"task {task_id} not found",
                )

            # Check task status
            if atask.status not in (TaskStatus.ACTIVE,):
                return GateResult(
                    decision=GateDecision.DENY,
                    action=action,
                    resource=resource,
                    task_id=task_id,
                    reason=f"task {task_id} is {atask.status.value}",
                )

            # Check task expiry
            if atask.expires_at and time.time() > atask.expires_at:
                return GateResult(
                    decision=GateDecision.DENY,
                    action=action,
                    resource=resource,
                    task_id=task_id,
                    reason=f"task {task_id} expired",
                )

            # Check capabilities
            if action not in atask.approval_policy:
                return GateResult(
                    decision=GateDecision.DENY,
                    action=action,
                    resource=resource,
                    task_id=task_id,
                    reason=f"action '{action}' not in task approval policy",
                )

            # INVARIANT: Agent cannot expand its own task scope
            # If action requires approval but task says autonomous, deny
            task_policy = atask.approval_policy.get(action)
            if task_policy == "autonomous" and policy_decision.verdict == Verdict.HUMAN:
                return GateResult(
                    decision=GateDecision.DENY,
                    action=action,
                    resource=resource,
                    task_id=task_id,
                    reason=f"agent cannot self-approve '{action}' — policy requires human, task says autonomous",
                )

            # Check data scope
            if atask.data_scope:
                resource_allowed = any(
                    self._resource_in_scope(resource, scope)
                    for scope in atask.data_scope
                )
                if not resource_allowed:
                    self._audit.log(
                        action=AuditAction.SECURITY_VIOLATION,
                        actor=agent,
                        task_id=task_id,
                        resource=resource,
                        details={"action": action, "violation": "scope_violation",
                                 "data_scope": atask.data_scope},
                        decision="DENY",
                        reason=f"resource {resource} not in task data scope",
                    )
                    return GateResult(
                        decision=GateDecision.DENY,
                        action=action,
                        resource=resource,
                        task_id=task_id,
                        reason=f"resource {resource} not in task data scope",
                    )

            # INVARIANT: Goal integrity — financial actions require budget > 0
            if policy_decision.side_effect >= SideEffect.FINANCIAL:
                if atask.money_budget is None or atask.money_budget.get("amount", 0) <= 0:
                    return GateResult(
                        decision=GateDecision.DENY,
                        action=action,
                        resource=resource,
                        task_id=task_id,
                        reason=f"financial action '{action}' requires task budget > 0 (goal integrity)",
                    )

            # Check budget
            if amount is not None and atask.money_budget:
                budget_amount = atask.money_budget.get("amount")
                if budget_amount is not None and amount > budget_amount:
                    return GateResult(
                        decision=GateDecision.DENY,
                        action=action,
                        resource=resource,
                        task_id=task_id,
                        reason=f"amount £{amount} exceeds task budget £{budget_amount}",
                    )

        # 5. HUMAN verdict → check for existing approval
        if policy_decision.verdict == Verdict.HUMAN:
            # Look for valid approval (pending or approved, not consumed/expired/revoked)
            usable = self._approvals.find_usable(action=action, resource=resource, task_id=task_id)

            if usable:
                # Use the first valid approval
                approval = usable[0]

                # INVARIANT: For human_principal_only actions, approval must be human-approved
                if policy_decision.human_principal_only and not approval.is_human_approved:
                    self._audit.log(
                        action=AuditAction.APPROVAL_DENIED,
                        actor=agent,
                        task_id=task_id,
                        resource=resource,
                        details={"action": action, "approval_id": approval.approval_id,
                                 "violation": "agent_minted_authority",
                                 "created_by": approval.created_by,
                                 "approved_by": approval.approved_by},
                        decision="DENY",
                        reason=f"approval {approval.approval_id} was not created by human principal "
                               f"(created_by={approval.created_by}, approved_by={approval.approved_by})",
                    )
                    return GateResult(
                        decision=GateDecision.DENY,
                        action=action,
                        resource=resource,
                        task_id=task_id,
                        reason=f"approval was not human-created (agents cannot mint authority)",
                    )

                if approval.is_valid():
                    self._audit.log(
                        action=AuditAction.APPROVAL_CONSUMED,
                        actor=agent,
                        task_id=task_id,
                        resource=resource,
                        details={"action": action, "approval_id": approval.approval_id,
                                 "created_by": approval.created_by,
                                 "approved_by": approval.approved_by},
                        decision="ALLOW",
                        reason=f"consumed approval {approval.approval_id}",
                    )
                    self._approvals.consume(approval.approval_id, actual_amount=amount)

                    # Find credential reference for this resource
                    injection = self._find_credential(action, resource, task_id)
                    if injection:
                        self._audit.log(
                            action=AuditAction.CREDENTIAL_INJECTED,
                            actor=agent,
                            task_id=task_id,
                            resource=resource,
                            details={"action": action, "ref_id": injection.ref.ref_id,
                                     "provider": injection.ref.provider},
                            decision="ALLOW",
                        )

                    return GateResult(
                        decision=GateDecision.ALLOW,
                        action=action,
                        resource=resource,
                        task_id=task_id,
                        injection=injection,
                        approval=approval,
                        reason=f"approved via {approval.approval_id}",
                    )

            # No approval → escalate to human
            self._audit.log(
                action=AuditAction.APPROVAL_DENIED,
                actor=agent,
                task_id=task_id,
                resource=resource,
                details={"action": action, "reason": "no_valid_approval"},
                decision="HUMAN",
                reason="requires human approval",
            )
            return GateResult(
                decision=GateDecision.HUMAN,
                action=action,
                resource=resource,
                task_id=task_id,
                reason="requires human approval",
            )

        # 6. AUTO verdict → proceed with credential injection
        injection = self._find_credential(action, resource, task_id)
        if injection:
            self._audit.log(
                action=AuditAction.CREDENTIAL_INJECTED,
                actor=agent,
                task_id=task_id,
                resource=resource,
                details={"action": action, "ref_id": injection.ref.ref_id,
                         "provider": injection.ref.provider},
                decision="ALLOW",
            )

        return GateResult(
            decision=GateDecision.ALLOW,
            action=action,
            resource=resource,
            task_id=task_id,
            injection=injection,
            reason=policy_decision.reason,
        )

    def _find_credential(
        self,
        action: str,
        resource: str,
        task_id: str | None,
    ) -> CredentialInjection | None:
        """Find and inject the right credential for this action/resource."""
        # Try exact action match first, then prefix match
        refs = self._broker.find_by_capability(action)
        if not refs:
            # Try prefix: "domain.purchase" → look for "domain.*" or "domain" in caps
            prefix = action.split(".")[0]
            refs = self._broker.find_by_capability(prefix)
        if not refs:
            # Try wildcard match
            for ref in self._broker.list_references():
                if any(action.startswith(cap.split(".")[0]) for cap in ref.capabilities):
                    refs = [ref]
                    break

        if refs:
            return self._broker.inject(refs[0].ref_id, task_id=task_id, action=action)
        return None

    def _resource_in_scope(self, resource: str, scope: str) -> bool:
        """Check if resource matches scope pattern."""
        if scope.endswith("**"):
            return resource.startswith(scope[:-2])
        if scope.endswith("*"):
            return resource.startswith(scope[:-1])
        return resource == scope
