"""Policy engine — per-resource-per-action rules.

Deterministic. Model cannot modify policies governing its own task.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    HUMAN = "human"
    FORBIDDEN = "forbidden"


@dataclass
class PolicyRule:
    """A single policy rule."""
    resource_type: str  # e.g. "cloudflare", "telnyx", "meta"
    action: str         # e.g. "dns.write", "domain.purchase", "phone.search"
    effect: Effect = Effect.ALLOW
    budget_max: float | None = None  # max cost per invocation
    budget_currency: str = "GBP"
    time_restrictions: list[str] = field(default_factory=list)  # e.g. "business_hours"
    description: str = ""

    def matches(self, resource_type: str, action: str) -> bool:
        if self.resource_type != "*" and self.resource_type != resource_type:
            return False
        if self.action != "*" and self.action != action:
            return False
        return True


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    effect: Effect
    rule: PolicyRule | None = None
    reason: str = ""
    budget_check: bool = True
    parameter_check: bool = True


class PolicyEngine:
    """Evaluates actions against policy rules.

    Rules are ordered: first match wins.
    DENY always takes precedence over ALLOW if both match.
    """
    def __init__(self):
        self._rules: list[PolicyRule] = []

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    def clear_rules(self) -> None:
        self._rules.clear()

    def evaluate(
        self,
        resource_type: str,
        action: str,
        cost: float = 0.0,
        params: dict | None = None,
    ) -> PolicyDecision:
        """Evaluate whether an action is permitted.

        Uses first-match-wins semantics. Rules are ordered; first matching
        rule determines the outcome.

        Args:
            resource_type: e.g. "cloudflare", "telnyx"
            action: e.g. "dns.write", "domain.purchase"
            cost: estimated cost of the action
            params: action parameters (for parameter validation)

        Returns:
            PolicyDecision with effect + reason
        """
        for rule in self._rules:
            if not rule.matches(resource_type, action):
                continue

            # First matching rule wins
            if rule.effect in (Effect.DENY, Effect.FORBIDDEN):
                return PolicyDecision(
                    effect=Effect.DENY,
                    rule=rule,
                    reason=rule.description or f"denied by policy: {resource_type}.{action}",
                )

            if rule.effect == Effect.HUMAN:
                if rule.budget_max is not None and cost > rule.budget_max:
                    return PolicyDecision(
                        effect=Effect.DENY,
                        rule=rule,
                        reason=f"budget exceeded: {cost} > {rule.budget_max} {rule.budget_currency}",
                        budget_check=False,
                    )
                return PolicyDecision(
                    effect=Effect.HUMAN,
                    rule=rule,
                    reason=rule.description or f"human approval required: {resource_type}.{action}",
                )

            if rule.effect == Effect.ALLOW:
                if rule.budget_max is not None and cost > rule.budget_max:
                    return PolicyDecision(
                        effect=Effect.DENY,
                        rule=rule,
                        reason=f"budget exceeded: {cost} > {rule.budget_max} {rule.budget_currency}",
                        budget_check=False,
                    )
                return PolicyDecision(
                    effect=Effect.ALLOW,
                    rule=rule,
                    reason=rule.description or f"allowed: {resource_type}.{action}",
                )

        # No matching rule → default deny
        return PolicyDecision(
            effect=Effect.DENY,
            reason=f"no policy found for {resource_type}.{action}",
        )

    def get_rules_for_resource(self, resource_type: str) -> list[PolicyRule]:
        return [r for r in self._rules if r.resource_type == resource_type or r.resource_type == "*"]

    def export_rules(self) -> list[dict]:
        return [
            {
                "resource_type": r.resource_type,
                "action": r.action,
                "effect": r.effect.value,
                "budget_max": r.budget_max,
                "budget_currency": r.budget_currency,
                "description": r.description,
            }
            for r in self._rules
        ]
