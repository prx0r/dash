"""Task Engine — A-Goal → A-Task → M-Task/H-Task hierarchy.

Every action in the system belongs to an ATask. No orphaned actions.
ATasks contain M-Tasks (machine-executable) and H-Tasks (human-required).

The task engine manages the lifecycle: create → execute → complete/fail.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(Enum):
    A_TASK = "a_task"  # composite: contains M/H tasks
    M_TASK = "m_task"  # machine-executable
    H_TASK = "h_task"  # human-required


class TaskStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MTask:
    """Machine-executable task. Contains the actual work to be done."""
    task_id: str
    action: str
    resource: str
    provider: str
    parameters: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class HTask:
    """Human-required task. Contains reason + estimated time."""
    task_id: str
    action: str
    resource: str
    reason: str
    estimated_minutes: float
    instructions: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class ATask:
    """Bounded unit of economic work. Contains M-Tasks and H-Tasks."""
    task_id: str
    goal: str
    principal: str
    agent: str
    company: str
    capabilities_required: list[str]
    approval_policy: dict[str, str]  # action → "autonomous"|"human_approval"|"forbidden"
    money_budget: dict[str, Any] | None = None
    time_budget: str | None = None
    data_scope: list[str] | None = None
    expected_outcome: str = ""
    validator: str = ""
    provenance: dict[str, str] | None = None
    status: TaskStatus = TaskStatus.PENDING
    m_tasks: list[MTask] = field(default_factory=list)
    h_tasks: list[HTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    @property
    def total_tasks(self) -> int:
        return len(self.m_tasks) + len(self.h_tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.m_tasks if t.status == TaskStatus.COMPLETED) + \
               sum(1 for t in self.h_tasks if t.status == TaskStatus.COMPLETED)

    @property
    def autonomy_rate(self) -> float:
        """Percentage of tasks completed by machine."""
        if self.total_tasks == 0:
            return 0.0
        machine_completed = sum(1 for t in self.m_tasks if t.status == TaskStatus.COMPLETED)
        return machine_completed / self.total_tasks

    @property
    def machine_tasks(self) -> int:
        return len(self.m_tasks)

    @property
    def human_tasks(self) -> int:
        return len(self.h_tasks)


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4).upper()}"


class TaskEngine:
    """Manages A-Task lifecycle."""

    def __init__(self):
        self._atasks: dict[str, ATask] = {}
        self._mtasks: dict[str, MTask] = {}
        self._htasks: dict[str, HTask] = {}

    def create_atask(
        self,
        goal: str,
        principal: str,
        agent: str,
        company: str,
        capabilities_required: list[str],
        approval_policy: dict[str, str],
        money_budget: dict[str, Any] | None = None,
        time_budget: str | None = None,
        data_scope: list[str] | None = None,
        expected_outcome: str = "",
        validator: str = "",
        provenance: dict[str, str] | None = None,
        ttl_hours: float = 24,
    ) -> ATask:
        """Create a new ATask."""
        task = ATask(
            task_id=_gen_id("A"),
            goal=goal,
            principal=principal,
            agent=agent,
            company=company,
            capabilities_required=capabilities_required,
            approval_policy=approval_policy,
            money_budget=money_budget,
            time_budget=time_budget,
            data_scope=data_scope,
            expected_outcome=expected_outcome,
            validator=validator,
            provenance=provenance,
            status=TaskStatus.ACTIVE,
            expires_at=time.time() + ttl_hours * 3600,
        )
        self._atasks[task.task_id] = task
        return task

    def add_mtask(
        self,
        atask_id: str,
        action: str,
        resource: str,
        provider: str,
        parameters: dict[str, Any] | None = None,
    ) -> MTask:
        """Add an M-Task to an ATask."""
        atask = self._atasks.get(atask_id)
        if not atask:
            raise ValueError(f"ATask {atask_id} not found")

        mtask = MTask(
            task_id=_gen_id("M"),
            action=action,
            resource=resource,
            provider=provider,
            parameters=parameters or {},
        )
        atask.m_tasks.append(mtask)
        self._mtasks[mtask.task_id] = mtask
        return mtask

    def add_htask(
        self,
        atask_id: str,
        action: str,
        resource: str,
        reason: str,
        estimated_minutes: float,
        instructions: str = "",
    ) -> HTask:
        """Add an H-Task to an ATask."""
        atask = self._atasks.get(atask_id)
        if not atask:
            raise ValueError(f"ATask {atask_id} not found")

        htask = HTask(
            task_id=_gen_id("H"),
            action=action,
            resource=resource,
            reason=reason,
            estimated_minutes=estimated_minutes,
            instructions=instructions,
        )
        atask.h_tasks.append(htask)
        self._htasks[htask.task_id] = htask
        return htask

    def complete_mtask(self, task_id: str, result: dict[str, Any] | None = None) -> MTask | None:
        """Complete an M-Task."""
        mtask = self._mtasks.get(task_id)
        if not mtask:
            return None
        mtask.status = TaskStatus.COMPLETED
        mtask.result = result
        mtask.completed_at = time.time()
        return mtask

    def complete_htask(self, task_id: str, result: dict[str, Any] | None = None) -> HTask | None:
        """Complete an H-Task."""
        htask = self._htasks.get(task_id)
        if not htask:
            return None
        htask.status = TaskStatus.COMPLETED
        htask.result = result
        htask.completed_at = time.time()
        return htask

    def get_atask(self, task_id: str) -> ATask | None:
        return self._atasks.get(task_id)

    def list_atasks(self, status: TaskStatus | None = None, company: str | None = None) -> list[ATask]:
        results = list(self._atasks.values())
        if status:
            results = [a for a in results if a.status == status]
        if company:
            results = [a for a in results if a.company == company]
        return results

    def ready_mtasks(self, atask_id: str) -> list[MTask]:
        """M-Tasks that are ready to execute (not blocked)."""
        atask = self._atasks.get(atask_id)
        if not atask:
            return []
        return [t for t in atask.m_tasks if t.status == TaskStatus.PENDING]

    def pending_htasks(self, atask_id: str) -> list[HTask]:
        """H-Tasks waiting for human."""
        atask = self._atasks.get(atask_id)
        if not atask:
            return []
        return [t for t in atask.h_tasks if t.status == TaskStatus.PENDING]

    def summary(self, atask_id: str) -> dict[str, Any]:
        """Task summary with AutonomyRate."""
        atask = self._atasks.get(atask_id)
        if not atask:
            return {}
        return {
            "task_id": atask.task_id,
            "goal": atask.goal,
            "status": atask.status.value,
            "machine_tasks": atask.machine_tasks,
            "human_tasks": atask.human_tasks,
            "completed": atask.completed_tasks,
            "autonomy_rate": f"{atask.autonomy_rate:.0%}",
            "m_completed": sum(1 for t in atask.m_tasks if t.status == TaskStatus.COMPLETED),
            "h_completed": sum(1 for t in atask.h_tasks if t.status == TaskStatus.COMPLETED),
        }
