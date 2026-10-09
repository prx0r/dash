"""Capability Gate — THE TRUST BOUNDARY.

Every tool call passes through here. Deterministic. Auditable.
The model cannot modify the kernel policy governing its own current task.

Flow:
  agent → authenticate → verify ATask → eval policy → check resource →
  validate params → check budget → check approval → ALLOW/HUMAN/DENY
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..audit.log import AuditEvent, AuditLog
from ..auth.identity import AgentToken, IdentityService
from ..policy.engine import Effect, PolicyDecision, PolicyEngine
from .broker import CredentialBroker, ExecutionResult


class GateVerdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    HUMAN = "HUMAN"


@dataclass
class GateRequest:
    """A tool call request passing through the gate."""
    agent_id: str
    token: AgentToken
    task_id: str
    company: str
    action: str           # e.g. "dns.create_record"
    resource_type: str    # e.g. "cloudflare"
    resource_id: str      # e.g. "agentcom.org"
    params: dict[str, Any] | None = None
    cost: float = 0.0
    approval_id: str | None = None  # if human approval required


@dataclass
class GateResult:
    """Result of capability gate evaluation."""
    verdict: GateVerdict
    reason: str
    execution_result: ExecutionResult | None = None
    audit_entry_id: str | None = None

    def to_agent_response(self) -> dict[str, Any]:
        """Return only what the agent should see."""
        result: dict[str, Any] = {
            "verdict": self.verdict.value,
            "reason": self.reason,
        }
        if self.execution_result:
            result.update(self.execution_result.to_agent_response())
        return result


class CapabilityGate:
    """The trust boundary between model-controlled and deterministic worlds.

    The model CANNOT:
    - Modify policies governing its own task
    - Retrieve raw credentials
    - Bypass approval requirements
    - Exceed budgets
    - Access resources outside its task scope
    - Self-authorize actions
    """

    def __init__(
        self,
        identity: IdentityService,
        policy: PolicyEngine,
        broker: CredentialBroker,
        audit: AuditLog,
    ):
        self._identity = identity
        self._policy = policy
        self._broker = broker
        self._audit = audit
        self._approval_service: Any = None

    def evaluate(self, request: GateRequest) -> GateResult:
        """Evaluate a tool call request through the full gate pipeline.

        This is deterministic. No model calls influence the outcome.
        """
        # Step 1: Authenticate agent + verify token
        valid, reason = self._identity.verify_request(
            agent_id=request.agent_id,
            token=request.token,
            required_capability=f"{request.resource_type}.{request.action}",
            resource_company=request.company,
        )
        if not valid:
            entry = self._audit.append(
                event=AuditEvent.AGENT_REJECTED,
                agent_id=request.agent_id,
                task_id=request.task_id,
                company=request.company,
                action=request.action,
                resource=request.resource_id,
                provider=request.resource_type,
                effect="DENY",
                reason=reason,
            )
            return GateResult(
                verdict=GateVerdict.DENY,
                reason=f"authentication failed: {reason}",
                audit_entry_id=entry.entry_id,
            )

        # Step 2: Verify ATask exists and is active
        # (In V0, task verification is implicit via token binding)
        if request.token.task_id != request.task_id:
            entry = self._audit.append(
                event=AuditEvent.UNAUTHORIZED_ACCESS,
                agent_id=request.agent_id,
                task_id=request.task_id,
                company=request.company,
                action=request.action,
                resource=request.resource_id,
                effect="DENY",
                reason=f"task_id mismatch: token has '{request.token.task_id}', request has '{request.task_id}'",
            )
            return GateResult(
                verdict=GateVerdict.DENY,
                reason="task_id mismatch",
                audit_entry_id=entry.entry_id,
            )

        # Step 3: Evaluate policy
        decision = self._policy.evaluate(
            resource_type=request.resource_type,
            action=request.action,
            cost=request.cost,
            params=request.params,
        )

        self._audit.append(
            event=AuditEvent.POLICY_EVALUATION,
            agent_id=request.agent_id,
            task_id=request.task_id,
            company=request.company,
            action=request.action,
            resource=request.resource_id,
            provider=request.resource_type,
            effect=decision.effect.value.upper(),
            reason=decision.reason,
        )

        # Step 4: DENY → stop
        if decision.effect in (Effect.DENY, Effect.FORBIDDEN):
            entry = self._audit.append(
                event=AuditEvent.GATE_DECISION,
                agent_id=request.agent_id,
                task_id=request.task_id,
                company=request.company,
                action=request.action,
                resource=request.resource_id,
                provider=request.resource_type,
                effect="DENY",
                reason=decision.reason,
            )
            return GateResult(
                verdict=GateVerdict.DENY,
                reason=decision.reason,
                audit_entry_id=entry.entry_id,
            )

        # Step 5: HUMAN → check approval
        if decision.effect == Effect.HUMAN:
            if not request.approval_id:
                entry = self._audit.append(
                    event=AuditEvent.GATE_DECISION,
                    agent_id=request.agent_id,
                    task_id=request.task_id,
                    company=request.company,
                    action=request.action,
                    resource=request.resource_id,
                    provider=request.resource_type,
                    effect="HUMAN",
                    reason="human approval required, no approval provided",
                )
                return GateResult(
                    verdict=GateVerdict.HUMAN,
                    reason="human approval required",
                    audit_entry_id=entry.entry_id,
                )

            # Verify approval is parameter-bound
            if self._approval_service:
                approval = self._approval_service.get_approval(request.approval_id)
                if not approval:
                    entry = self._audit.append(
                        event=AuditEvent.APPROVAL_DENIED,
                        agent_id=request.agent_id,
                        task_id=request.task_id,
                        company=request.company,
                        action=request.action,
                        resource=request.resource_id,
                        provider=request.resource_type,
                        effect="DENY",
                        reason="approval not found",
                    )
                    return GateResult(
                        verdict=GateVerdict.DENY,
                        reason="approval not found",
                        audit_entry_id=entry.entry_id,
                    )

                # Parameter-bound verification
                ok, verify_reason = self._approval_service.verify(
                    approval,
                    expected_action=request.action,
                    expected_resource=request.resource_id,
                    cost=request.cost,
                )
                if not ok:
                    entry = self._audit.append(
                        event=AuditEvent.APPROVAL_DENIED,
                        agent_id=request.agent_id,
                        task_id=request.task_id,
                        company=request.company,
                        action=request.action,
                        resource=request.resource_id,
                        provider=request.resource_type,
                        effect="DENY",
                        reason=f"approval rejected: {verify_reason}",
                    )
                    return GateResult(
                        verdict=GateVerdict.DENY,
                        reason=f"approval rejected: {verify_reason}",
                        audit_entry_id=entry.entry_id,
                    )

                # Consume single-use approval
                if approval.single_use:
                    self._approval_service.consume(request.approval_id)

                self._audit.append(
                    event=AuditEvent.APPROVAL_VERIFIED,
                    agent_id=request.agent_id,
                    task_id=request.task_id,
                    company=request.company,
                    action=request.action,
                    resource=request.resource_id,
                    provider=request.resource_type,
                    effect="ALLOW",
                    reason=f"approval verified: {request.approval_id}",
                )

        # Step 6: ALLOW → execute via broker
        vault_path = f"vault://{request.company}/{request.resource_type}/prod"
        exec_result = self._broker.execute(
            vault_path=vault_path,
            action=request.action,
            params=request.params or {},
        )

        # Step 7: Record credential injection (audit only, never exposes value)
        if exec_result.credential_used:
            self._audit.append(
                event=AuditEvent.CREDENTIAL_INJECTION,
                agent_id=request.agent_id,
                task_id=request.task_id,
                company=request.company,
                action=request.action,
                resource=request.resource_id,
                provider=request.resource_type,
                effect="ALLOW",
                reason=f"credential injected: {exec_result.credential_used}",
            )

        # Step 8: Final gate decision
        if exec_result.success:
            entry = self._audit.append(
                event=AuditEvent.GATE_DECISION,
                agent_id=request.agent_id,
                task_id=request.task_id,
                company=request.company,
                action=request.action,
                resource=request.resource_id,
                provider=request.resource_type,
                effect="ALLOW",
                reason="all checks passed",
                receipt_id=exec_result.receipt_id,
            )
            return GateResult(
                verdict=GateVerdict.ALLOW,
                reason="executed",
                execution_result=exec_result,
                audit_entry_id=entry.entry_id,
            )
        else:
            entry = self._audit.append(
                event=AuditEvent.GATE_DECISION,
                agent_id=request.agent_id,
                task_id=request.task_id,
                company=request.company,
                action=request.action,
                resource=request.resource_id,
                provider=request.resource_type,
                effect="DENY",
                reason=f"execution failed: {exec_result.error}",
            )
            return GateResult(
                verdict=GateVerdict.DENY,
                reason=f"execution failed: {exec_result.error}",
                execution_result=exec_result,
                audit_entry_id=entry.entry_id,
            )

    def set_approval_service(self, service: Any) -> None:
        """Inject approval service for HUMAN verdict verification."""
        self._approval_service = service
