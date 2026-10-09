"""Credential Broker — inject credentials internally, never expose to agent.

Invariant: No model-controlled execution environment can retrieve a reusable credential.

The agent sends: {"tool": "dns.create_record", "params": {"name": "mcp.agentcom.org"}}
The broker sends to provider: {"Authorization": "Bearer sk_..."} (injected internally)
The agent receives: {"success": true, "record_id": "abc"}

The agent NEVER sees sk_...
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CredentialReference:
    """A reference to a credential. The actual value is never stored in the graph."""
    vault_path: str          # e.g. "vault://agentcom/cloudflare/prod"
    capabilities: list[str] = field(default_factory=list)
    exposure_policy: str = "never"  # "never" | "audit_only"
    provider: str = ""
    description: str = ""


@dataclass
class ExecutionResult:
    """Sanitized result returned to the agent."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    receipt_id: str | None = None
    credential_used: str | None = None  # vault_path, never the actual key

    def to_agent_response(self) -> dict[str, Any]:
        """Return ONLY what the agent should see. No credentials."""
        result: dict[str, Any] = {"success": self.success}
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.receipt_id:
            result["receipt_id"] = self.receipt_id
        return result


class CredentialBroker:
    """Injects credentials at execution time. Never exposes them.

    Trust boundary: this class is deterministic.
    The model cannot call methods on itself to extract credentials.
    """

    def __init__(self):
        self._credentials: dict[str, CredentialReference] = {}
        self._providers: dict[str, Callable] = {}
        self._credential_store: dict[str, str] = {}  # vault_path -> actual value

    def register_credential(
        self,
        vault_path: str,
        provider: str,
        capabilities: list[str],
        actual_value: str,
        description: str = "",
    ) -> CredentialReference:
        """Register a credential. The actual value is stored separately."""
        ref = CredentialReference(
            vault_path=vault_path,
            capabilities=capabilities,
            provider=provider,
            description=description,
        )
        self._credentials[vault_path] = ref
        self._credential_store[vault_path] = actual_value
        return ref

    def register_provider(self, provider: str, handler: Callable) -> None:
        """Register a provider execution handler."""
        self._providers[provider] = handler

    def execute(
        self,
        vault_path: str,
        action: str,
        params: dict[str, Any],
    ) -> ExecutionResult:
        """Execute an action with credential injection.

        The agent calls: broker.execute("vault://cloudflare/prod", "dns.create", {...})
        The broker:
        1. Looks up the credential reference
        2. Retrieves the actual value internally
        3. Calls the provider handler with the credential
        4. Returns sanitized result to the agent

        The agent NEVER sees the credential value.
        """
        ref = self._credentials.get(vault_path)
        if not ref:
            return ExecutionResult(
                success=False,
                error=f"credential not found: {vault_path}",
            )

        actual_key = self._credential_store.get(vault_path)
        if not actual_key:
            return ExecutionResult(
                success=False,
                error=f"credential value missing: {vault_path}",
            )

        handler = self._providers.get(ref.provider)
        if not handler:
            return ExecutionResult(
                success=False,
                error=f"no handler for provider: {ref.provider}",
            )

        try:
            # Inject credential internally. Agent never sees this.
            raw_result = handler(action=action, params=params, credential=actual_key)

            # Sanitize: strip credential from result
            sanitized = self._sanitize(raw_result)

            return ExecutionResult(
                success=True,
                data=sanitized,
                credential_used=vault_path,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                credential_used=vault_path,
            )

    def get_capability_for_credential(self, vault_path: str) -> list[str]:
        """Return capabilities granted by this credential. Never the value."""
        ref = self._credentials.get(vault_path)
        return ref.capabilities if ref else []

    def list_credentials(self) -> list[dict[str, str]]:
        """Return credential references. Never actual values."""
        return [
            {
                "vault_path": ref.vault_path,
                "provider": ref.provider,
                "capabilities": ref.capabilities,
                "description": ref.description,
            }
            for ref in self._credentials.values()
        ]

    def _sanitize(self, data: Any) -> Any:
        """Remove credential material from provider response."""
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                k_lower = k.lower()
                if any(s in k_lower for s in ["key", "token", "secret", "password", "auth", "credential"]):
                    # Redact all credential fields completely
                    cleaned[k] = "[REDACTED]"
                else:
                    cleaned[k] = self._sanitize(v)
            return cleaned
        elif isinstance(data, list):
            return [self._sanitize(item) for item in data]
        return data
