"""Approval System — parameter-bound human authorization.

INVARIANT: Agents cannot mint authority. An agent may REQUEST authority,
EXPLAIN why authority is required, WAIT for authority, USE granted authority.
It may never CREATE authority, SIMULATE human approval, or EDIT approval records.

Approvals bind to specific action + resource + parameters. An approval for
"buy agentbeauty.io for £10" cannot be reused to buy "malicious-domain.xyz".

Only human principals (human:*) can create and approve. Agent principals
(agent:*) can only REQUEST and CONSUME.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Approval:
    """Parameter-bound human approval. Cannot be reused across actions/resources."""
    approval_id: str
    task_id: str
    action: str
    resource: str
    provider: str
    max_amount: float | None = None
    currency: str = "GBP"
    parameters: dict[str, Any] = field(default_factory=dict)
    expires_at: float | None = None
    single_use: bool = True
    # WHO created this approval — must be human:* for financial/privileged actions
    created_by: str = ""  # "human:tom" or "agent:cmail"
    approved_by: str | None = None
    approved_at: float | None = None
    status: str = "pending"  # pending, approved, consumed, expired, revoked
    consumed_at: float | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at and time.time() > self.expires_at:
            return True
        return self.status == "expired"

    def is_valid(self) -> bool:
        return (
            self.status == "approved"
            and not self.is_expired
            and not (self.single_use and self.status == "consumed")
        )

    @property
    def is_human_approved(self) -> bool:
        """Was this approval APPROVED by a human principal?

        Agents can REQUEST authority. Only humans can APPROVE it.
        The key check is approved_by, not created_by — because in the real
        flow, the agent requests and the human approves.

        Requires approved_by to be "human:<username>" where username is non-empty.
        """
        if not self.approved_by:
            return False
        if not self.approved_by.startswith("human:"):
            return False
        # Require non-empty username after "human:"
        return len(self.approved_by) > len("human:")


def _binding_hash(action: str, resource: str, parameters: dict[str, Any]) -> str:
    """Create a deterministic hash of the approval binding."""
    canonical = json.dumps({"action": action, "resource": resource, "parameters": sorted(parameters.items())}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class ApprovalSystem:
    """Manages parameter-bound approvals.

    INVARIANT: Agents cannot mint authority.
    - request() can be called by anyone (agent or human) — it creates a PENDING request
    - approve() MUST be called by a human principal — agents cannot approve
    - For side_effect >= 3 (FINANCIAL), only human:* principals can approve
    """

    def __init__(self):
        self._approvals: dict[str, Approval] = {}
        self._bindings: dict[str, str] = {}  # binding_hash → approval_id

    def request(
        self,
        task_id: str,
        action: str,
        resource: str,
        provider: str,
        max_amount: float | None = None,
        currency: str = "GBP",
        parameters: dict[str, Any] | None = None,
        ttl_seconds: float = 3600,
        requested_by: str = "agent:unknown",
    ) -> Approval:
        """Request an approval. Returns pending approval.

        Anyone can REQUEST. Only human principals can APPROVE.
        """
        parameters = parameters or {}
        approval_id = "APR-" + secrets.token_hex(8).upper()

        approval = Approval(
            approval_id=approval_id,
            task_id=task_id,
            action=action,
            resource=resource,
            provider=provider,
            max_amount=max_amount,
            currency=currency,
            parameters=parameters,
            expires_at=time.time() + ttl_seconds,
            status="pending",
            created_by=requested_by,
        )

        self._approvals[approval_id] = approval

        # Store binding hash for replay detection
        binding = _binding_hash(action, resource, parameters)
        self._bindings[binding] = approval_id

        return approval

    def approve(
        self,
        approval_id: str,
        approved_by: str,
        action: str | None = None,
        resource: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Approval | None:
        """Approve a pending request. Validates parameter binding.

        INVARIANT: Only human principals can approve. Agents cannot mint authority.
        """
        approval = self._approvals.get(approval_id)
        if not approval or approval.status != "pending":
            return None

        # INVARIANT: Only human principals can approve
        # Requires "human:<username>" where username is non-empty
        if not approved_by or not approved_by.startswith("human:") or len(approved_by) <= len("human:"):
            return None  # AGENT CANNOT APPROVE

        # Validate that the approval hasn't been tampered with
        if action and action != approval.action:
            return None
        if resource and resource != approval.resource:
            return None

        # Re-check binding hash
        params = parameters or approval.parameters
        binding = _binding_hash(approval.action, approval.resource, params)
        stored_binding = _binding_hash(approval.action, approval.resource, approval.parameters)
        if binding != stored_binding:
            return None

        updated = Approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            action=approval.action,
            resource=approval.resource,
            provider=approval.provider,
            max_amount=approval.max_amount,
            currency=approval.currency,
            parameters=approval.parameters,
            expires_at=approval.expires_at,
            single_use=approval.single_use,
            created_by=approval.created_by,
            approved_by=approved_by,
            approved_at=time.time(),
            status="approved",
        )
        self._approvals[approval_id] = updated
        return updated

    def consume(self, approval_id: str, actual_amount: float | None = None) -> bool:
        """Consume an approval. Checks amount bounds and single-use."""
        approval = self._approvals.get(approval_id)
        if not approval or not approval.is_valid():
            return False

        # Check amount bounds
        if actual_amount is not None and approval.max_amount is not None:
            if actual_amount > approval.max_amount:
                return False

        if approval.single_use:
            updated = Approval(
                approval_id=approval.approval_id,
                task_id=approval.task_id,
                action=approval.action,
                resource=approval.resource,
                provider=approval.provider,
                max_amount=approval.max_amount,
                currency=approval.currency,
                parameters=approval.parameters,
                expires_at=approval.expires_at,
                single_use=approval.single_use,
                created_by=approval.created_by,
                approved_by=approval.approved_by,
                approved_at=approval.approved_at,
                status="consumed",
                consumed_at=time.time(),
            )
            self._approvals[approval_id] = updated
        return True

    def revoke(self, approval_id: str) -> bool:
        """Revoke an approval."""
        approval = self._approvals.get(approval_id)
        if not approval:
            return False
        updated = Approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            action=approval.action,
            resource=approval.resource,
            provider=approval.provider,
            max_amount=approval.max_amount,
            currency=approval.currency,
            parameters=approval.parameters,
            expires_at=approval.expires_at,
            single_use=approval.single_use,
            created_by=approval.created_by,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at,
            status="revoked",
        )
        self._approvals[approval_id] = updated
        return True

    def get(self, approval_id: str) -> Approval | None:
        return self._approvals.get(approval_id)

    def find_for_task(self, task_id: str) -> list[Approval]:
        return [a for a in self._approvals.values() if a.task_id == task_id]

    def find_usable(self, action: str | None = None, resource: str | None = None, task_id: str | None = None) -> list[Approval]:
        """Find approvals that can be consumed (pending or approved, not expired/consumed/revoked)."""
        results = [a for a in self._approvals.values() if a.is_valid()]
        if action:
            results = [a for a in results if a.action == action]
        if resource:
            results = [a for a in results if a.resource == resource]
        if task_id:
            results = [a for a in results if a.task_id == task_id]
        return results

    def find_pending(self, action: str | None = None, resource: str | None = None) -> list[Approval]:
        results = [a for a in self._approvals.values() if a.status == "pending"]
        if action:
            results = [a for a in results if a.action == action]
        if resource:
            results = [a for a in results if a.resource == resource]
        return results

    def expire_stale(self) -> list[str]:
        """Expire old approvals. Returns expired IDs."""
        expired = []
        for aid, approval in self._approvals.items():
            if approval.status == "pending" and approval.is_expired:
                updated = Approval(
                    approval_id=approval.approval_id,
                    task_id=approval.task_id,
                    action=approval.action,
                    resource=approval.resource,
                    provider=approval.provider,
                    max_amount=approval.max_amount,
                    currency=approval.currency,
                    parameters=approval.parameters,
                    expires_at=approval.expires_at,
                    single_use=approval.single_use,
                    created_by=approval.created_by,
                    status="expired",
                )
                self._approvals[aid] = updated
                expired.append(aid)
        return expired
