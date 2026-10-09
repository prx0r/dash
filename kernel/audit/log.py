"""Audit log — immutable, append-only trail.

Every Gate decision, every credential injection, every policy eval.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuditEvent(str, Enum):
    GATE_DECISION = "gate_decision"
    CREDENTIAL_INJECTION = "credential_injection"
    POLICY_EVALUATION = "policy_evaluation"
    APPROVAL_VERIFIED = "approval_verified"
    APPROVAL_DENIED = "approval_denied"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_AUTHENTICATED = "agent_authenticated"
    AGENT_REJECTED = "agent_rejected"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class AuditEntry:
    """A single immutable audit entry."""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    event: AuditEvent = AuditEvent.GATE_DECISION
    agent_id: str = ""
    task_id: str = ""
    company: str = ""
    action: str = ""
    resource: str = ""
    provider: str = ""
    effect: str = ""  # ALLOW / DENY / HUMAN
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    receipt_id: str | None = None


class AuditLog:
    """Append-only audit trail.

    In production: D1 table. In V0: in-memory list.
    The model cannot modify, delete, or read the audit log
    except through approved query interfaces.
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []

    def append(
        self,
        event: AuditEvent,
        agent_id: str = "",
        task_id: str = "",
        company: str = "",
        action: str = "",
        resource: str = "",
        provider: str = "",
        effect: str = "",
        reason: str = "",
        details: dict[str, Any] | None = None,
        receipt_id: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            event=event,
            agent_id=agent_id,
            task_id=task_id,
            company=company,
            action=action,
            resource=resource,
            provider=provider,
            effect=effect,
            reason=reason,
            details=details or {},
            receipt_id=receipt_id,
        )
        self._entries.append(entry)
        return entry

    def query(
        self,
        agent_id: str | None = None,
        task_id: str | None = None,
        company: str | None = None,
        event: AuditEvent | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = self._entries
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        if task_id:
            results = [e for e in results if e.task_id == task_id]
        if company:
            results = [e for e in results if e.company == company]
        if event:
            results = [e for e in results if e.event == event]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def count(
        self,
        effect: str | None = None,
        event: AuditEvent | None = None,
        since: float | None = None,
    ) -> int:
        results = self._entries
        if effect:
            results = [e for e in results if e.effect == effect]
        if event:
            results = [e for e in results if e.event == event]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return len(results)

    def stats(self) -> dict[str, Any]:
        total = len(self._entries)
        denied = sum(1 for e in self._entries if e.effect == "DENY")
        allowed = sum(1 for e in self._entries if e.effect == "ALLOW")
        human = sum(1 for e in self._entries if e.effect == "HUMAN")
        return {
            "total_events": total,
            "allowed": allowed,
            "denied": denied,
            "human_required": human,
            "denial_rate": denied / total if total > 0 else 0.0,
        }
