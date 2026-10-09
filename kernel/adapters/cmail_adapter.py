"""Cmail Adapter — bridges cmail MCP tools to the Agentcom Kernel.

Every action is linked to a company ID. The company ID is the root node
of the graph. All resources (domains, emails, phones, socials) attach to it.

Usage:
    from agentcom.kernel.adapters.cmail_adapter import CmailAdapter

    adapter = CmailAdapter.from_vault()

    # Create company identity
    company = adapter.create_company("Agentcom", "agent-commerce", "GB", "human:tom")

    # Check domain (linked to company)
    result = adapter.execute("name.cf_check", {"domain": "pog.pet"},
                             company_id=company.company_id, task_id="A-0001")
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Callable

from ..capabilities import CapabilityGate, GateDecision
from ..credentials import CredentialBroker
from ..policy import PolicyEngine, PolicyRule, Verdict, SideEffect
from ..approvals import ApprovalSystem
from ..audit import AuditLog, AuditAction
from ..tasks import TaskEngine, TaskStatus
from ..graph.identity import IdentityService, CompanyIdentity


class CmailAdapter:
    """Bridges cmail MCP tools to the Capability Gate.

    Every action is linked to a company_id. The company is the root
    of the graph — all resources attach to it.
    """

    # Tool → (action, resource_template, provider, side_effect)
    TOOL_MAP = {
        "name.search":       ("domain.check",   "cloudflare/domain/{name}",   "cloudflare", SideEffect.PURE),
        "name.cf_check":     ("domain.check",   "cloudflare/domain/{domain}", "cloudflare", SideEffect.PURE),
        "name.cf_purchase":  ("domain.purchase","cloudflare/domain/{domain}", "cloudflare", SideEffect.FINANCIAL),
        "name.wire_email":   ("email.write",    "cloudflare/email/{domain}",  "cloudflare", SideEffect.REVERSIBLE),
        "name.phone_search": ("phone.search",   "telnyx/phone/{country}",     "telnyx",     SideEffect.PURE),
        "name.phone_purchase":("phone.purchase","telnyx/phone/{number}",      "telnyx",     SideEffect.FINANCIAL),
        "name.social":       ("social.check",   "social/{name}",              "social",     SideEffect.PURE),
        "name.check_handles":("social.check",   "social/{name}",              "social",     SideEffect.PURE),
        "email.send":        ("email.send",     "cloudflare/email/{to}",      "cloudflare", SideEffect.EXTERNAL),
        "email.draft":       ("email.write",    "cloudflare/email/{to}",      "cloudflare", SideEffect.REVERSIBLE),
        "email.reply":       ("email.write",    "cloudflare/email/{to}",      "cloudflare", SideEffect.REVERSIBLE),
    }

    def __init__(
        self,
        gate: CapabilityGate,
        broker: CredentialBroker,
        audit: AuditLog,
        tasks: TaskEngine,
        identity: IdentityService,
        cmail_url: str = "https://cmail.tradesprior.workers.dev/mcp",
    ):
        self._gate = gate
        self._broker = broker
        self._audit = audit
        self._tasks = tasks
        self._identity = identity
        self._cmail_url = cmail_url

    def create_company(
        self,
        name: str,
        vertical: str,
        country: str,
        principal: str,
        attributes: dict[str, Any] | None = None,
    ) -> CompanyIdentity:
        """Create a company identity. Returns stable ID.

        This is the root node of the graph. Everything else attaches here.
        """
        return self._identity.create(name, vertical, country, principal, attributes)

    def get_company(self, company_id: str) -> CompanyIdentity | None:
        return self._identity.get(company_id)

    def can_execute(
        self,
        tool: str,
        args: dict[str, Any],
        company_id: str | None = None,
        task_id: str | None = None,
        agent: str = "unknown",
    ) -> dict[str, Any]:
        """Check if a tool call is allowed. Returns decision without executing.

        Every check is linked to a company_id if provided.
        """
        mapping = self.TOOL_MAP.get(tool)
        if not mapping:
            return {
                "allowed": False,
                "decision": "DENY",
                "reason": f"unknown tool: {tool}",
                "company_id": company_id,
            }

        action, resource_template, provider, side_effect = mapping
        resource = self._resolve_resource(resource_template, args)

        # Prefix resource with company_id for graph linking
        if company_id:
            resource = f"{company_id}/{resource}"

        result = self._gate.check(
            action=action,
            resource=resource,
            task_id=task_id,
            agent=agent,
            amount=args.get("amount"),
            parameters=args,
        )

        return {
            "allowed": result.decision == GateDecision.ALLOW,
            "decision": result.decision.value,
            "reason": result.reason,
            "needs_human": result.decision == GateDecision.HUMAN,
            "company_id": company_id,
            "action": action,
            "resource": resource,
            "side_effect": side_effect.name,
            "injection": {
                "ref_id": result.injection.ref.ref_id,
                "provider": result.injection.ref.provider,
            } if result.injection else None,
        }

    def execute(
        self,
        tool: str,
        args: dict[str, Any],
        company_id: str | None = None,
        task_id: str | None = None,
        agent: str = "unknown",
        executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool through the Capability Gate.

        Every execution is linked to a company_id and logged in the audit trail.
        """
        check = self.can_execute(tool, args, company_id, task_id, agent)

        if not check["allowed"]:
            self._audit.log(
                action=AuditAction.GATE_DECISION,
                actor=agent,
                task_id=task_id,
                resource=check.get("resource", ""),
                details={
                    "tool": tool,
                    "company_id": company_id,
                    "args_keys": list(args.keys()),
                    "side_effect": check.get("side_effect"),
                },
                decision=check["decision"],
                reason=check["reason"],
            )
            return {
                "error": check["decision"],
                "reason": check["reason"],
                "tool": tool,
                "company_id": company_id,
            }

        # Execute through the provided executor
        if executor:
            try:
                result = executor(tool, args)
                self._audit.log(
                    action=AuditAction.GATE_DECISION,
                    actor=agent,
                    task_id=task_id,
                    resource=check.get("resource", ""),
                    details={
                        "tool": tool,
                        "company_id": company_id,
                        "outcome": "success",
                    },
                    decision="ALLOW",
                )
                # Link result to company
                if company_id and isinstance(result, dict):
                    result["company_id"] = company_id
                return result
            except Exception as e:
                self._audit.log(
                    action=AuditAction.TASK_FAILED,
                    actor=agent,
                    task_id=task_id,
                    resource=check.get("resource", ""),
                    details={
                        "tool": tool,
                        "company_id": company_id,
                        "error": str(e),
                    },
                    decision="DENY",
                )
                return {"error": str(e), "tool": tool, "company_id": company_id}

        # No executor — just return the gate decision
        return {
            "decision": check["decision"],
            "reason": check["reason"],
            "tool": tool,
            "company_id": company_id,
            "note": "gate allowed but no executor provided",
        }

    def _resolve_resource(self, template: str, args: dict[str, Any]) -> str:
        """Resolve resource template with args."""
        resource = template
        for key, value in args.items():
            if isinstance(value, str):
                resource = resource.replace(f"{{{key}}}", value)
        return resource

    @classmethod
    def from_vault(cls, cmail_url: str | None = None) -> "CmailAdapter":
        """Create adapter with vault-backed credentials."""
        policy = PolicyEngine.default_policy()
        broker = CredentialBroker.from_vault()
        approvals = ApprovalSystem()
        audit = AuditLog()
        tasks = TaskEngine()
        identity = IdentityService()
        gate = CapabilityGate(policy, broker, approvals, audit, tasks)

        return cls(
            gate=gate,
            broker=broker,
            audit=audit,
            tasks=tasks,
            identity=identity,
            cmail_url=cmail_url or "https://cmail.tradesprior.workers.dev/mcp",
        )
