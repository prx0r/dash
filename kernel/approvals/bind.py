"""Parameter-bound approval tokens.

An approval for domain.purchase on agentbeauty.io does NOT
authorize domain.purchase on malicious-domain.xyz.

Binding is to: action + resource + amount + expiry.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field


@dataclass
class Approval:
    """A parameter-bound, time-limited, single-use approval."""
    approval_id: str = field(default_factory=lambda: f"APR-{secrets.token_hex(4).upper()}")
    task_id: str = ""
    action: str = ""           # e.g. "domain.purchase"
    resource: str = ""         # e.g. "agentbeauty.io"
    provider: str = ""         # e.g. "cloudflare"
    max_amount: float = 0.0
    currency: str = "GBP"
    single_use: bool = True
    expires_at: float = 0.0
    issued_at: float = field(default_factory=time.time)
    signature: str = ""
    consumed: bool = False
    consumed_at: float | None = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_consumed(self) -> bool:
        return self.consumed


class ApprovalService:
    """Manages parameter-bound approvals.

    The trust boundary: approvals are issued by humans through
    a deterministic verification path. The model cannot self-issue approvals.
    """

    def __init__(self, signing_key: str | None = None):
        self._signing_key = signing_key or secrets.token_hex(32)
        self._approvals: dict[str, Approval] = {}

    def issue(
        self,
        task_id: str,
        action: str,
        resource: str,
        provider: str,
        max_amount: float,
        currency: str = "GBP",
        ttl_seconds: int = 3600,
        single_use: bool = True,
    ) -> Approval:
        """Issue a parameter-bound approval. Called by human verification path."""
        now = time.time()
        approval = Approval(
            task_id=task_id,
            action=action,
            resource=resource,
            provider=provider,
            max_amount=max_amount,
            currency=currency,
            single_use=single_use,
            expires_at=now + ttl_seconds,
            issued_at=now,
        )
        approval.signature = self._sign(approval)
        self._approvals[approval.approval_id] = approval
        return approval

    def verify(
        self,
        approval: Approval,
        expected_action: str,
        expected_resource: str,
        cost: float = 0.0,
    ) -> tuple[bool, str]:
        """Verify an approval is valid and matches the requested action.

        Checks:
        1. Approval exists and signature is valid
        2. Not expired
        3. Not consumed (if single-use)
        4. Action matches exactly
        5. Resource matches exactly
        6. Cost within budget
        """
        stored = self._approvals.get(approval.approval_id)
        if not stored:
            return False, "approval not found"

        expected_sig = self._sign(stored)
        if not hmac.compare_digest(approval.signature, expected_sig):
            return False, "invalid signature"

        if stored.is_expired():
            return False, "approval expired"

        if stored.consumed:
            return False, "approval already consumed"

        if stored.action != expected_action:
            return False, f"action mismatch: approved '{stored.action}', requested '{expected_action}'"

        if stored.resource != expected_resource:
            return False, f"resource mismatch: approved '{stored.resource}', requested '{expected_resource}'"

        if cost > stored.max_amount:
            return False, f"cost {cost} exceeds approved max {stored.max_amount} {stored.currency}"

        if stored.task_id:
            pass  # task binding verified by gate, not here

        return True, "ok"

    def consume(self, approval_id: str) -> bool:
        """Mark an approval as consumed (single-use)."""
        approval = self._approvals.get(approval_id)
        if not approval or approval.consumed:
            return False
        approval.consumed = True
        approval.consumed_at = time.time()
        return True

    def get_approval(self, approval_id: str) -> Approval | None:
        return self._approvals.get(approval_id)

    def revoke(self, approval_id: str) -> bool:
        if approval_id in self._approvals:
            del self._approvals[approval_id]
            return True
        return False

    def _sign(self, approval: Approval) -> str:
        payload = json.dumps({
            "approval_id": approval.approval_id,
            "task_id": approval.task_id,
            "action": approval.action,
            "resource": approval.resource,
            "provider": approval.provider,
            "max_amount": approval.max_amount,
            "currency": approval.currency,
            "expires_at": approval.expires_at,
        }, sort_keys=True)
        return hmac.new(
            self._signing_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
