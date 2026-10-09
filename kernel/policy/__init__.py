"""Policy Engine — deterministic per-resource, per-action policy evaluation.

The model cannot modify the kernel policy governing its own current task.
Policies are evaluated before credential injection. The engine is pure:
input state → verdict. No I/O.

Invariant: No model-controlled execution environment can retrieve a reusable
credential. The policy engine is part of the deterministic trust boundary.

NEW INVARIANT (after $8.50 incident):
Agents cannot mint authority. An agent may REQUEST authority, EXPLAIN why
authority is required, WAIT for authority, USE granted authority. It may
never CREATE authority, SIMULATE human approval, EDIT approval records,
WRITE its own policy, EXPAND its task scope, EXPAND its budget, or
CHANGE approval requirements.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Any


class SideEffect(IntEnum):
    """Classification of action side effects. Model cannot downgrade.

    0 PURE        — read-only, no mutation
    1 REVERSIBLE  — can be undone (drafts, temporary records)
    2 EXTERNAL    — sends data outside the system (email, SMS, social)
    3 FINANCIAL   — involves money (purchases, refunds, ad spend)
    4 PRIVILEGED  — changes system authority (credentials, permissions)
    5 IRREVERSIBLE — cannot be undone (deletion, large transfers)
    """
    PURE = 0
    REVERSIBLE = 1
    EXTERNAL = 2
    FINANCIAL = 3
    PRIVILEGED = 4
    IRREVERSIBLE = 5


class Verdict(Enum):
    ALLOW = "allow"
    DENY = "deny"
    HUMAN = "human"  # requires human approval/execution
    FORBIDDEN = "forbidden"  # permanently blocked


@dataclass(frozen=True)
class PolicyRule:
    """A single policy rule for an action on a resource."""
    action: str
    resource_pattern: str  # glob pattern: "cloudflare/dns/*", "cloudflare/domain/*"
    verdict: Verdict
    side_effect: SideEffect = SideEffect.PURE
    max_amount: float | None = None  # monetary ceiling
    currency: str = "GBP"
    time_restrictions: dict[str, Any] | None = None  # future: time-of-day
    reason: str = ""
    # Can the agent ever self-approve this? Even with an approval object?
    human_principal_only: bool = False  # if True, only human:* principals can approve


@dataclass(frozen=True)
class PolicyDecision:
    """Result of policy evaluation."""
    verdict: Verdict
    action: str
    resource: str
    rule: PolicyRule | None
    reason: str
    side_effect: SideEffect = SideEffect.PURE
    human_principal_only: bool = False
    checked_at: float = field(default_factory=time.time)


class PolicyEngine:
    """Deterministic policy evaluation. No I/O. Pure function on state."""

    def __init__(self, rules: list[PolicyRule] | None = None):
        self._rules: list[PolicyRule] = rules or []
        self._rules.sort(key=lambda r: (
            len(r.resource_pattern),  # most specific first
            r.verdict.value,
        ))

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: (len(r.resource_pattern), r.verdict.value))

    def evaluate(
        self,
        action: str,
        resource: str,
        amount: float | None = None,
        task_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Evaluate a single action against policy. Pure function."""
        context = context or {}

        for rule in self._rules:
            if rule.action != action:
                continue
            if not self._matches_resource(rule.resource_pattern, resource):
                continue

            # Check monetary limit
            if rule.max_amount is not None and amount is not None:
                if amount > rule.max_amount:
                    return PolicyDecision(
                        verdict=Verdict.DENY,
                        action=action,
                        resource=resource,
                        rule=rule,
                        reason=f"amount £{amount} exceeds policy limit £{rule.max_amount}",
                        side_effect=rule.side_effect,
                        human_principal_only=rule.human_principal_only,
                    )

            return PolicyDecision(
                verdict=rule.verdict,
                action=action,
                resource=resource,
                rule=rule,
                reason=rule.reason or f"matched rule: {rule.action} on {rule.resource_pattern}",
                side_effect=rule.side_effect,
                human_principal_only=rule.human_principal_only,
            )

        # Default: deny unknown actions (fail-closed)
        return PolicyDecision(
            verdict=Verdict.DENY,
            action=action,
            resource=resource,
            rule=None,
            reason=f"no policy rule for action '{action}' on resource '{resource}'",
        )

    def _matches_resource(self, pattern: str, resource: str) -> bool:
        """Simple glob matching: * matches any single segment, ** matches any path.

        Handles company-prefixed resources: COMP-XXX/cloudflare/domain/test.com
        matches pattern cloudflare/domain/* because we skip the company prefix.
        """
        pattern_parts = pattern.strip("/").split("/")
        resource_parts = resource.strip("/").split("/")

        # Special case: pattern is just "*" — matches everything
        if pattern == "*":
            return True

        # If resource has a COMP- prefix, try matching without it
        if resource_parts and resource_parts[0].startswith("COMP-"):
            resource_parts_no_prefix = resource_parts[1:]
            if self._glob_match(pattern_parts, resource_parts_no_prefix):
                return True

        return self._glob_match(pattern_parts, resource_parts)

    def _glob_match(self, pattern: list[str], resource: list[str]) -> bool:
        pi, ri = 0, 0
        while pi < len(pattern) and ri < len(resource):
            if pattern[pi] == "**":
                if pi == len(pattern) - 1:
                    return True
                pi += 1
                while ri < len(resource):
                    if self._glob_match(pattern[pi:], resource[ri:]):
                        return True
                    ri += 1
                return False
            elif pattern[pi] == "*" or pattern[pi] == resource[ri]:
                pi += 1
                ri += 1
            else:
                return False
        return pi == len(pattern) and ri == len(resource)

    @classmethod
    def default_policy(cls) -> "PolicyEngine":
        """Default policy for Agentcom kernel.

        INVARIANT: Agents cannot mint authority. Approval for side_effect >= 3
        (FINANCIAL) requires human_principal_only. The agent can REQUEST but
        never CREATE approval for financial/privileged/irreversible actions.
        """
        return cls(rules=[
            # Reads are always allowed (side_effect = PURE)
            PolicyRule("read", "*", Verdict.ALLOW, SideEffect.PURE,
                        reason="reads never mutate"),

            # DNS operations (REVERSIBLE)
            PolicyRule("dns.read", "cloudflare/dns/*", Verdict.ALLOW, SideEffect.PURE),
            PolicyRule("dns.write", "cloudflare/dns/*", Verdict.ALLOW, SideEffect.REVERSIBLE,
                        reason="DNS writes are reversible"),

            # Domain operations
            PolicyRule("domain.check", "cloudflare/domain/*", Verdict.ALLOW, SideEffect.PURE),
            PolicyRule("domain.purchase", "cloudflare/domain/*", Verdict.HUMAN,
                        SideEffect.FINANCIAL, max_amount=50.0,
                        human_principal_only=True,
                        reason="domain purchase requires human approval"),
            PolicyRule("domain.transfer", "cloudflare/domain/*", Verdict.FORBIDDEN,
                        SideEffect.IRREVERSIBLE,
                        reason="domain transfers are forbidden"),

            # Email operations
            PolicyRule("email.read", "cloudflare/email/*", Verdict.ALLOW, SideEffect.PURE),
            PolicyRule("email.write", "cloudflare/email/*", Verdict.ALLOW, SideEffect.REVERSIBLE,
                        reason="email routing is reversible"),
            PolicyRule("email.send", "cloudflare/email/*", Verdict.HUMAN, SideEffect.EXTERNAL,
                        human_principal_only=True,
                        reason="outbound email requires human approval"),

            # Phone operations
            PolicyRule("phone.search", "telnyx/phone/*", Verdict.ALLOW, SideEffect.PURE),
            PolicyRule("phone.purchase", "telnyx/phone/*", Verdict.HUMAN, SideEffect.FINANCIAL,
                        max_amount=10.0, human_principal_only=True,
                        reason="phone purchase requires human approval"),
            PolicyRule("phone.sms", "telnyx/phone/*", Verdict.HUMAN, SideEffect.EXTERNAL,
                        human_principal_only=True,
                        reason="SMS requires human approval"),

            # Social operations
            PolicyRule("social.check", "social/*", Verdict.ALLOW, SideEffect.PURE),
            PolicyRule("social.register", "social/*", Verdict.HUMAN, SideEffect.EXTERNAL,
                        human_principal_only=True,
                        reason="social registration requires human approval"),

            # Credential operations — AGENT CAN NEVER READ CREDENTIALS
            PolicyRule("credential.read", "*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot read raw credentials"),
            PolicyRule("credential.list", "*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot enumerate credentials"),

            # Approval operations — AGENT CAN NEVER CREATE/MINT AUTHORITY
            PolicyRule("approval.create", "*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        human_principal_only=True,
                        reason="agent cannot create approvals — authority comes from human principal only"),
            PolicyRule("approval.modify", "*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot modify approval records"),

            # Policy operations — AGENT CAN NEVER MODIFY ITS OWN POLICY
            PolicyRule("policy.read", "kernel/policy/*", Verdict.ALLOW, SideEffect.PURE,
                        reason="agent can read policy for planning"),
            PolicyRule("policy.write", "kernel/policy/*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot modify its own policy"),

            # Budget operations
            PolicyRule("budget.read", "kernel/budget/*", Verdict.ALLOW, SideEffect.PURE),
            PolicyRule("budget.write", "kernel/budget/*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot modify its own budget"),

            # Task scope operations
            PolicyRule("task.scope.expand", "*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot expand its own task scope"),
            PolicyRule("task.budget.expand", "*", Verdict.FORBIDDEN, SideEffect.PRIVILEGED,
                        reason="agent cannot expand its own budget"),

            # Cross-company access — FORBIDDEN
            PolicyRule("company.read", "*/company/*", Verdict.ALLOW, SideEffect.PURE,
                        reason="agent can read own company"),
            PolicyRule("company.read", "**/company/*", Verdict.DENY, SideEffect.PURE,
                        reason="agent cannot access other companies"),
        ])
