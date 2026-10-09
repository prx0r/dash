"""getsocials — the capability onboarding procedure.

The guiding question: is it POSSIBLE for an agent to post on insta,
to email, to have a website? The agent doesn't care about content.
It cares about credentials and capabilities.

getsocials splits into subroutines. Each subroutine follows the same
shape: check → claim/approve → verify → connect.

    getsocials/
    ├── domain/    check → purchase (H) → done
    ├── email/     wire → verify
    ├── phone/     search → purchase (H)
    ├── insta/     check → claim (H) → verify → connect
    ├── x/         check → claim (H) → verify → connect
    └── youtube/   check → claim (H) → verify → connect

Every step has prerequisites. When prerequisites complete, downstream
steps unlock. H-tasks appear in the queue when their dependencies are met.

The DAG is the visual representation of the graph's missing nodes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(Enum):
    LOCKED = "locked"       # dependencies not met
    READY = "ready"         # dependencies met, can start
    RUNNING = "running"     # in progress
    DONE = "done"           # completed
    BLOCKED = "blocked"     # waiting for human


class StepType(Enum):
    M_TASK = "m_task"       # machine autonomous
    H_TASK = "h_task"       # human required


@dataclass
class GetsocialsStep:
    step_id: str
    subroutine: str         # domain | email | phone | insta | x | youtube | ...
    name: str
    description: str
    step_type: StepType
    action: str             # kernel action (e.g. domain.check)
    resource: str           # kernel resource pattern
    provider: str
    status: StepStatus = StepStatus.LOCKED
    depends_on: list[str] = field(default_factory=list)  # step_ids
    estimated_minutes: float = 0
    human_instructions: str = ""
    result: dict[str, Any] | None = None


# Backwards-compat alias
OnboardingStep = GetsocialsStep


def _s(step_id: str, subroutine: str, name: str, description: str,
       step_type: StepType, action: str, resource: str, provider: str,
       depends_on: list[str] | None = None, estimated_minutes: float = 0,
       human_instructions: str = "") -> GetsocialsStep:
    return GetsocialsStep(
        step_id=step_id, subroutine=subroutine, name=name,
        description=description, step_type=step_type, action=action,
        resource=resource, provider=provider,
        depends_on=depends_on or [],
        estimated_minutes=estimated_minutes,
        human_instructions=human_instructions,
    )


# The canonical getsocials DAG for any company.
# Subroutines are independent except where noted; social connects
# need email + phone because platforms verify via both.
GETSOCIALS_STEPS = [
    # ── domain/ ──
    _s("domain_check", "domain", "Check domain availability",
       "Verify target domain is available across registrars",
       StepType.M_TASK, "domain.check", "cloudflare/domain/{domain}", "cloudflare"),
    _s("domain_purchase", "domain", "Purchase domain",
       "Buy domain via Cloudflare Registrar (~$8-10/yr)",
       StepType.H_TASK, "domain.purchase", "cloudflare/domain/{domain}", "cloudflare",
       depends_on=["domain_check"], estimated_minutes=2,
       human_instructions="Review domain and price, confirm purchase"),

    # ── email/ (needs domain) ──
    _s("email_wire", "email", "Wire email routing",
       "Set up Cloudflare Email Routing → cmail worker",
       StepType.M_TASK, "email.write", "cloudflare/email/{domain}", "cloudflare",
       depends_on=["domain_purchase"]),
    _s("email_verify", "email", "Verify email works",
       "Send test email, confirm receipt in cmail inbox",
       StepType.M_TASK, "email.read", "cloudflare/email/{domain}", "cloudflare",
       depends_on=["email_wire"]),

    # ── phone/ (independent of domain) ──
    _s("phone_search", "phone", "Search phone numbers",
       "Find best local/mobile/toll-free number via Telnyx",
       StepType.M_TASK, "phone.search", "telnyx/phone/{country}", "telnyx"),
    _s("phone_purchase", "phone", "Purchase phone number",
       "Buy number via Telnyx (~$2/mo)",
       StepType.H_TASK, "phone.purchase", "telnyx/phone/{number}", "telnyx",
       depends_on=["phone_search"], estimated_minutes=3,
       human_instructions="Review number options, confirm purchase"),

    # ── insta/ (needs email + phone for verification) ──
    _s("insta_check", "insta", "Check Instagram handle",
       "Verify @handle availability on Instagram",
       StepType.M_TASK, "social.check", "social/instagram/{name}", "instagram"),
    _s("insta_claim", "insta", "Claim Instagram handle",
       "Human creates the Instagram account (platforms block bots)",
       StepType.H_TASK, "social.register", "social/instagram/{name}", "instagram",
       depends_on=["insta_check", "email_verify"], estimated_minutes=5,
       human_instructions="Create account in Instagram app, verify via email"),
    _s("insta_verify", "insta", "Verify Instagram handle resolves",
       "Machine confirms @handle page exists",
       StepType.M_TASK, "social.check", "social/instagram/{name}", "instagram",
       depends_on=["insta_claim"]),
    _s("insta_connect", "insta", "Connect Instagram API",
       "OAuth connect for post/read/DM via Postiz",
       StepType.H_TASK, "social.connect", "social/instagram/{name}", "instagram",
       depends_on=["insta_verify", "phone_purchase"], estimated_minutes=3,
       human_instructions="One OAuth click, approve permissions"),

    # ── x/ ──
    _s("x_check", "x", "Check X handle",
       "Verify @handle availability on X",
       StepType.M_TASK, "social.check", "social/x/{name}", "x"),
    _s("x_claim", "x", "Claim X handle",
       "Human creates the X account (platforms block bots)",
       StepType.H_TASK, "social.register", "social/x/{name}", "x",
       depends_on=["x_check", "email_verify"], estimated_minutes=5,
       human_instructions="Create account on x.com, verify via email"),
    _s("x_verify", "x", "Verify X handle resolves",
       "Machine confirms @handle page exists",
       StepType.M_TASK, "social.check", "social/x/{name}", "x",
       depends_on=["x_claim"]),
    _s("x_connect", "x", "Connect X API",
       "API key connect for post/read via Postiz",
       StepType.H_TASK, "social.connect", "social/x/{name}", "x",
       depends_on=["x_verify", "phone_purchase"], estimated_minutes=3,
       human_instructions="Generate API keys in developer portal, paste into Postiz"),

    # ── youtube/ ──
    _s("youtube_check", "youtube", "Check YouTube handle",
       "Verify @handle availability on YouTube",
       StepType.M_TASK, "social.check", "social/youtube/{name}", "youtube"),
    _s("youtube_claim", "youtube", "Claim YouTube channel",
       "Human creates the channel (needs Google account)",
       StepType.H_TASK, "social.register", "social/youtube/{name}", "youtube",
       depends_on=["youtube_check", "email_verify"], estimated_minutes=3,
       human_instructions="Create channel, verify via Google account"),
    _s("youtube_verify", "youtube", "Verify YouTube channel resolves",
       "Machine confirms @handle page exists",
       StepType.M_TASK, "social.check", "social/youtube/{name}", "youtube",
       depends_on=["youtube_claim"]),
    _s("youtube_connect", "youtube", "Connect YouTube API",
       "OAuth connect for upload/analytics",
       StepType.H_TASK, "social.connect", "social/youtube/{name}", "youtube",
       depends_on=["youtube_verify", "phone_purchase"], estimated_minutes=3,
       human_instructions="One OAuth click in Google Cloud console"),
]

# Backwards-compat alias
ONBOARDING_STEPS = GETSOCIALS_STEPS


class GetsocialsDAG:
    """Manages the getsocials dependency graph.

    Tracks which steps are done, which are ready, which are locked.
    When a step completes, auto-unlocks downstream steps.
    Subroutines can be paused independently — locked steps just wait.
    """

    def __init__(self, company_id: str, domain: str = "", name: str = "", country: str = "GB"):
        self.company_id = company_id
        self.domain = domain
        self.name = name
        self.country = country
        self._steps: dict[str, GetsocialsStep] = {}
        self._init_steps()

    def _init_steps(self):
        """Initialize steps from template."""
        for template in GETSOCIALS_STEPS:
            step = GetsocialsStep(
                step_id=template.step_id,
                subroutine=template.subroutine,
                name=template.name,
                description=template.description,
                step_type=template.step_type,
                action=template.action,
                resource=template.resource.replace("{domain}", self.domain)
                    .replace("{name}", self.name)
                    .replace("{country}", self.country),
                provider=template.provider,
                status=StepStatus.READY if not template.depends_on else StepStatus.LOCKED,
                depends_on=template.depends_on,
                estimated_minutes=template.estimated_minutes,
                human_instructions=template.human_instructions,
            )
            self._steps[step.step_id] = step

    def _blank(self) -> GetsocialsStep:
        return GetsocialsStep(step_id="", subroutine="", name="", description="",
                              step_type=StepType.M_TASK, action="", resource="", provider="")

    def complete(self, step_id: str, result: dict[str, Any] | None = None) -> list[GetsocialsStep]:
        """Mark a step as done. Returns newly unlocked steps."""
        step = self._steps.get(step_id)
        if not step:
            return []

        step.status = StepStatus.DONE
        step.result = result

        # Check if any downstream steps are now unblocked
        unlocked = []
        for s in self._steps.values():
            if s.status == StepStatus.LOCKED:
                all_deps_done = all(
                    self._steps.get(dep, self._blank()).status == StepStatus.DONE
                    for dep in s.depends_on
                )
                if all_deps_done:
                    s.status = StepStatus.READY
                    unlocked.append(s)

        return unlocked

    def get_step(self, step_id: str) -> GetsocialsStep | None:
        return self._steps.get(step_id)

    def ready_steps(self) -> list[GetsocialsStep]:
        """Steps that are ready to execute."""
        return [s for s in self._steps.values() if s.status == StepStatus.READY]

    def pending_h_tasks(self) -> list[GetsocialsStep]:
        """Human tasks that are ready (dependencies met, waiting for human)."""
        return [s for s in self._steps.values()
                if s.step_type == StepType.H_TASK and s.status == StepStatus.READY]

    def locked_steps(self) -> list[GetsocialsStep]:
        """Steps blocked by unmet dependencies."""
        return [s for s in self._steps.values() if s.status == StepStatus.LOCKED]

    def completed_steps(self) -> list[GetsocialsStep]:
        return [s for s in self._steps.values() if s.status == StepStatus.DONE]

    def subroutine_status(self, subroutine: str) -> dict[str, Any]:
        """Status of one subroutine: what % is done, what's blocking it."""
        steps = [s for s in self._steps.values() if s.subroutine == subroutine]
        if not steps:
            return {"subroutine": subroutine, "total": 0, "done": 0, "status": "unknown"}
        done = sum(1 for s in steps if s.status == StepStatus.DONE)
        blockers = sorted({d for s in steps if s.status == StepStatus.LOCKED
                           for d in s.depends_on
                           if self._steps.get(d, self._blank()).status != StepStatus.DONE})
        return {
            "subroutine": subroutine,
            "total": len(steps),
            "done": done,
            "progress_pct": f"{done / len(steps) * 100:.0f}%",
            "status": "done" if done == len(steps) else "in_progress" if done else "not_started",
            "blocked_by": blockers,
        }

    def subroutines(self) -> list[dict[str, Any]]:
        """Status of every subroutine."""
        seen: list[str] = []
        for s in self._steps.values():
            if s.subroutine not in seen:
                seen.append(s.subroutine)
        return [self.subroutine_status(sub) for sub in seen]

    def progress(self) -> dict[str, Any]:
        """getsocials progress summary."""
        total = len(self._steps)
        done = len(self.completed_steps())
        ready = len(self.ready_steps())
        locked = len(self.locked_steps())
        h_tasks = len(self.pending_h_tasks())
        m_tasks = len([s for s in self.ready_steps() if s.step_type == StepType.M_TASK])

        return {
            "company_id": self.company_id,
            "total": total,
            "done": done,
            "ready": ready,
            "locked": locked,
            "h_tasks_pending": h_tasks,
            "m_tasks_ready": m_tasks,
            "progress_pct": f"{done / total * 100:.0f}%" if total else "0%",
        }

    def render(self) -> str:
        """Visual DAG representation, grouped by subroutine."""
        lines = []
        lines.append(f"GETSOCIALS: {self.company_id}")
        lines.append(f"{'=' * 60}")

        seen: list[str] = []
        for s in self._steps.values():
            if s.subroutine not in seen:
                seen.append(s.subroutine)

        for sub in seen:
            sub_steps = [s for s in self._steps.values() if s.subroutine == sub]
            st = self.subroutine_status(sub)
            lines.append(f"\n  {sub}/ [{st['done']}/{st['total']}] {st['status']}")
            for step in sub_steps:
                status_icon = {
                    StepStatus.DONE: "DONE",
                    StepStatus.READY: "TODO",
                    StepStatus.RUNNING: "...",
                    StepStatus.LOCKED: "---",
                    StepStatus.BLOCKED: "WAIT",
                }[step.status]
                type_icon = "M" if step.step_type == StepType.M_TASK else "H"
                deps = ""
                if step.status == StepStatus.LOCKED:
                    unmet = [d for d in step.depends_on
                             if self._steps.get(d, self._blank()).status != StepStatus.DONE]
                    if unmet:
                        deps = f" (waiting: {', '.join(unmet)})"
                lines.append(f"    [{status_icon:4s}] {type_icon} {step.name}{deps}")

        lines.append(f"\n{'=' * 60}")
        p = self.progress()
        lines.append(f"  Progress: {p['done']}/{p['total']} ({p['progress_pct']})")
        lines.append(f"  M-tasks ready: {p['m_tasks_ready']}")
        lines.append(f"  H-tasks pending: {p['h_tasks_pending']}")
        lines.append(f"  Locked: {p['locked']}")

        return "\n".join(lines)


# Backwards-compat alias
OnboardingDAG = GetsocialsDAG
