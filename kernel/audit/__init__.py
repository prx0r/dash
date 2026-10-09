"""Audit Log — immutable append-only trail of every kernel decision.

Every Capability Gate decision, credential injection, policy evaluation,
and approval action is logged. The audit log is append-only and queryable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuditAction(Enum):
    POLICY_EVALUATED = "policy_evaluated"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_CONSUMED = "approval_consumed"
    APPROVAL_DENIED = "approval_denied"
    CREDENTIAL_INJECTED = "credential_injected"
    CAPABILITY_CHECK = "capability_check"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    GATE_DECISION = "gate_decision"
    SECURITY_VIOLATION = "security_violation"


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit log entry."""
    entry_id: str
    timestamp: float
    action: AuditAction
    actor: str  # agent or user_id
    task_id: str | None
    resource: str | None
    details: dict[str, Any]
    decision: str | None = None  # ALLOW/DENY/HUMAN/FORBIDDEN
    reason: str | None = None


class AuditLog:
    """Append-only audit log. Immutable entries."""

    def __init__(self):
        self._entries: list[AuditEntry] = []
        self._counter = 0

    def log(
        self,
        action: AuditAction,
        actor: str,
        task_id: str | None = None,
        resource: str | None = None,
        details: dict[str, Any] | None = None,
        decision: str | None = None,
        reason: str | None = None,
    ) -> AuditEntry:
        """Append an audit entry. Never modifies existing entries."""
        self._counter += 1
        entry = AuditEntry(
            entry_id=f"AUD-{self._counter:08d}",
            timestamp=time.time(),
            action=action,
            actor=actor,
            task_id=task_id,
            resource=resource,
            details=details or {},
            decision=decision,
            reason=reason,
        )
        self._entries.append(entry)
        return entry

    def query(
        self,
        action: AuditAction | None = None,
        actor: str | None = None,
        task_id: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries. Returns newest first."""
        results = list(self._entries)
        if action:
            results = [e for e in results if e.action == action]
        if actor:
            results = [e for e in results if e.actor == actor]
        if task_id:
            results = [e for e in results if e.task_id == task_id]
        if since:
            results = [e for e in results if e.timestamp >= since]
        results.reverse()
        return results[:limit]

    def count(self, action: AuditAction | None = None) -> int:
        if action:
            return sum(1 for e in self._entries if e.action == action)
        return len(self._entries)

    def recent_violations(self, limit: int = 20) -> list[AuditEntry]:
        """Recent security violations."""
        return self.query(action=AuditAction.SECURITY_VIOLATION, limit=limit)
