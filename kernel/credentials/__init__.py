"""Credential Broker — injects credentials internally, never exposes them.

Invariant: No model-controlled execution environment can retrieve a reusable
credential. The broker stores credentials as references and injects them
only at execution time, inside the deterministic trust boundary.

The model sees: {"resource": "cloudflare/account/123", "capabilities": ["dns.write"]}
The model never sees: the actual API key
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class CredentialReference:
    """A reference to a credential. The actual value is never exposed."""
    ref_id: str
    provider: str  # cloudflare, telnyx, apify, etc.
    resource: str  # cloudflare/account/123
    capabilities: list[str]  # what this credential can do
    vault_path: str  # where the real credential lives (never exposed)
    expires_at: float | None = None
    max_usage: int | None = None
    usage_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.expires_at and time.time() > self.expires_at:
            return True
        if self.max_usage and self.usage_count >= self.max_usage:
            return True
        return False


@dataclass(frozen=True)
class CredentialInjection:
    """Result of credential injection. Contains the credential for internal use only."""
    ref: CredentialReference
    credential_value: str  # ONLY exists inside the trust boundary
    injected_at: float = field(default_factory=time.time)
    task_id: str | None = None


class CredentialBroker:
    """Stores credentials as references. Injects at execution time.

    The broker is the ONLY component that touches raw credentials.
    It lives inside the deterministic trust boundary.
    """

    def __init__(self, vault_getter: Callable[[str], str] | None = None):
        self._vault_getter = vault_getter
        self._references: dict[str, CredentialReference] = {}
        self._injections: list[dict[str, Any]] = []  # audit log (no values)

    def register(
        self,
        provider: str,
        resource: str,
        capabilities: list[str],
        vault_path: str,
        expires_in: float | None = None,
        max_usage: int | None = None,
    ) -> CredentialReference:
        """Register a credential reference. vault_path is stored but value never exposed."""
        ref_id = "CR-" + secrets.token_hex(8).upper()
        ref = CredentialReference(
            ref_id=ref_id,
            provider=provider,
            resource=resource,
            capabilities=capabilities,
            vault_path=vault_path,
            expires_at=time.time() + expires_in if expires_in else None,
            max_usage=max_usage,
        )
        self._references[ref_id] = ref
        return ref

    def get_reference(self, ref_id: str) -> CredentialReference | None:
        """Get a reference (no credential value). Safe for model access."""
        return self._references.get(ref_id)

    def list_references(self, provider: str | None = None) -> list[CredentialReference]:
        """List references (no credential values). Safe for model access."""
        refs = list(self._references.values())
        if provider:
            refs = [r for r in refs if r.provider == provider]
        return refs

    def find_by_capability(self, capability: str) -> list[CredentialReference]:
        """Find references that have a specific capability."""
        return [
            ref for ref in self._references.values()
            if capability in ref.capabilities and not ref.is_expired
        ]

    def inject(
        self,
        ref_id: str,
        task_id: str | None = None,
        action: str | None = None,
    ) -> CredentialInjection | None:
        """Inject credential for internal execution. Returns value ONLY inside trust boundary.

        This method should NEVER be called from model-controlled code.
        It is called by the Capability Gate after all checks pass.
        """
        ref = self._references.get(ref_id)
        if not ref or ref.is_expired:
            return None

        if not self._vault_getter:
            return None

        # Retrieve the actual credential from vault
        credential_value = self._vault_getter(ref.vault_path)
        if not credential_value:
            return None

        # Update usage count (in production, this would be atomic)
        # For now, create a new reference with incremented count
        updated = CredentialReference(
            ref_id=ref.ref_id,
            provider=ref.provider,
            resource=ref.resource,
            capabilities=ref.capabilities,
            vault_path=ref.vault_path,
            expires_at=ref.expires_at,
            max_usage=ref.max_usage,
            usage_count=ref.usage_count + 1,
        )
        self._references[ref_id] = updated

        # Audit log — NEVER log the credential value
        self._injections.append({
            "ref_id": ref_id,
            "task_id": task_id,
            "action": action,
            "provider": ref.provider,
            "resource": ref.resource,
            "injected_at": time.time(),
        })

        return CredentialInjection(
            ref=ref,
            credential_value=credential_value,
            task_id=task_id,
        )

    def revoke(self, ref_id: str) -> bool:
        """Revoke a credential reference."""
        if ref_id in self._references:
            del self._references[ref_id]
            return True
        return False

    def audit_log(self) -> list[dict[str, Any]]:
        """Return audit log of injections (no credential values)."""
        return list(self._injections)

    @classmethod
    def from_vault(cls, vault_command: str = "agent-vault") -> "CredentialBroker":
        """Create broker that reads from agent-vault."""
        import subprocess

        def vault_getter(path: str) -> str:
            key_name = path.split("/")[-1]  # e.g. "CLOUDFLARE_API_TOKEN" from "vault/cloudflare/CLOUDFLARE_API_TOKEN"
            result = subprocess.run(
                [vault_command, "vault", "credential", "get", key_name, "--vault", "oracle"],
                capture_output=True, text=True,
            )
            return result.stdout.strip() if result.returncode == 0 else ""

        broker = cls(vault_getter=vault_getter)

        # Register known credentials
        creds = [
            ("cloudflare", "cloudflare/account", ["dns.read", "dns.write", "domain.check", "domain.purchase", "email.write"],
             "vault/cloudflare/CLOUDFLARE_API_TOKEN"),
            ("cloudflare", "cloudflare/registrar", ["domain.purchase"],
             "vault/cloudflare/CLOUDFLARE_REGISTRAR_TOKEN"),
            ("telnyx", "telnyx/phone", ["phone.search", "phone.purchase", "phone.sms"],
             "vault/telnyx/TELNYX_API_KEY"),
            ("apify", "apify/scraping", ["social.check"],
             "vault/apify/APIFY_TOKEN"),
        ]
        for provider, resource, caps, vault_path in creds:
            broker.register(provider, resource, caps, vault_path)

        return broker
