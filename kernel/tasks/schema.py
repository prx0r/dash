"""Task schema — ATask (composite), MTask (machine), HTask (human), XTask (external).

A-TASK is the atomic unit of economic work.
M/H/X are children, not peers.

Every action in the system belongs to an ATask.
No orphaned actions.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskKind(str, Enum):
    ATASK = "atask"
    MTASK = "mtask"
    HTASK = "htask"
    XTASK = "xtask"


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPolicy(str, Enum):
    AUTONOMOUS = "autonomous"
    HUMAN_APPROVAL = "human_approval"
    FORBIDDEN = "forbidden"


def _make_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4).upper()}"


@dataclass
class MTask:
    """Machine-executable task. Runs autonomously within policy bounds."""
    task_id: str = field(default_factory=lambda: _make_id("M"))
    goal: str = ""
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    resource: str = ""
    capabilities_required: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class HTask:
    """Human task. Requires human action or authority. Cannot be automated."""
    task_id: str = field(default_factory=lambda: _make_id("H"))
    goal: str = ""
    reason: str = ""
    estimated_seconds: int = 0
    instructions: str = ""
    resource: str = ""
    status: TaskStatus = TaskStatus.PENDING
    completed_at: float | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class XTask:
    """External dependency. Wait for platform/system response."""
    task_id: str = field(default_factory=lambda: _make_id("X"))
    goal: str = ""
    provider: str = ""
    wait_for: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class ATask:
    """Bounded unit of economic work. Contains M/H/X children."""
    task_id: str = field(default_factory=lambda: _make_id("A"))
    goal: str = ""
    principal: str = ""
    agent: str = ""
    company: str = ""
    capabilities_required: list[str] = field(default_factory=list)
    money_budget: float = 0.0
    currency: str = "GBP"
    time_budget_seconds: int = 3600
    data_scope: list[str] = field(default_factory=list)
    approval_policy: dict[str, str] = field(default_factory=dict)
    expected_outcome: str = ""
    validator: str = ""
    provenance: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    mtasks: list[MTask] = field(default_factory=list)
    htasks: list[HTask] = field(default_factory=list)
    xtasks: list[XTask] = field(default_factory=list)
    spent: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    expires_at: float | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def children(self) -> list[MTask | HTask | XTask]:
        return list(self.mtasks) + list(self.htasks) + list(self.xtasks)

    def all_completed(self) -> bool:
        return all(
            c.status == TaskStatus.COMPLETED
            for c in self.children()
        )

    def any_failed(self) -> bool:
        return any(
            c.status == TaskStatus.FAILED
            for c in self.children()
        )

    def budget_remaining(self) -> float:
        return max(0.0, self.money_budget - self.spent)


def create_atask(
    goal: str,
    principal: str,
    agent: str,
    company: str,
    capabilities: list[str],
    budget: float = 0.0,
    currency: str = "GBP",
    time_budget: int = 3600,
    approval_policy: dict[str, str] | None = None,
    validator: str = "",
    provenance: list[str] | None = None,
) -> ATask:
    return ATask(
        goal=goal,
        principal=principal,
        agent=agent,
        company=company,
        capabilities_required=capabilities,
        money_budget=budget,
        currency=currency,
        time_budget_seconds=time_budget,
        approval_policy=approval_policy or {},
        validator=validator,
        provenance=provenance or [],
        expires_at=time.time() + time_budget,
    )


def create_mtask(
    goal: str,
    tool: str,
    params: dict[str, Any] | None = None,
    resource: str = "",
    capabilities: list[str] | None = None,
) -> MTask:
    return MTask(
        goal=goal,
        tool=tool,
        params=params or {},
        resource=resource,
        capabilities_required=capabilities or [],
    )


def create_htask(
    goal: str,
    reason: str,
    estimated_seconds: int = 300,
    instructions: str = "",
    resource: str = "",
) -> HTask:
    return HTask(
        goal=goal,
        reason=reason,
        estimated_seconds=estimated_seconds,
        instructions=instructions,
        resource=resource,
    )
