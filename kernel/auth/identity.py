"""Agent identity + ATask token verification.

The model CANNOT modify the kernel policy governing its own current task.
Identity is deterministic and verifiable.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field


@dataclass
class AgentIdentity:
    """Verified identity of an agent making a tool call."""
    agent_id: str
    company: str
    capabilities: list[str] = field(default_factory=list)
    token: str = ""
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at if self.expires_at else True

    def has_capability(self, cap: str) -> bool:
        return cap in self.capabilities or "admin" in self.capabilities


@dataclass
class AgentToken:
    """Short-lived token binding an agent to a specific ATask."""
    token_id: str = ""
    agent_id: str = ""
    task_id: str = ""
    company: str = ""
    capabilities: list[str] = field(default_factory=list)
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    signature: str = ""

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class IdentityService:
    """Manages agent identities and token verification.

    The trust boundary: this service is deterministic.
    The model cannot call methods on itself to forge identity.
    """

    def __init__(self, signing_key: str | None = None):
        self._signing_key = signing_key or secrets.token_hex(32)
        self._identities: dict[str, AgentIdentity] = {}
        self._tokens: dict[str, AgentToken] = {}

    def register_agent(
        self,
        agent_id: str,
        company: str,
        capabilities: list[str],
    ) -> AgentIdentity:
        identity = AgentIdentity(
            agent_id=agent_id,
            company=company,
            capabilities=capabilities,
        )
        self._identities[agent_id] = identity
        return identity

    def issue_token(
        self,
        agent_id: str,
        task_id: str,
        capabilities: list[str],
        ttl_seconds: int = 900,
    ) -> AgentToken:
        identity = self._identities.get(agent_id)
        if not identity:
            raise ValueError(f"unknown agent: {agent_id}")

        now = time.time()
        token = AgentToken(
            token_id=f"tok-{secrets.token_hex(8)}",
            agent_id=agent_id,
            task_id=task_id,
            company=identity.company,
            capabilities=capabilities,
            issued_at=now,
            expires_at=now + ttl_seconds,
        )
        token.signature = self._sign(token)
        self._tokens[token.token_id] = token
        return token

    def verify_token(self, token: AgentToken) -> tuple[bool, str]:
        """Verify a token is valid and not expired."""
        if token.is_expired():
            return False, "token expired"

        stored = self._tokens.get(token.token_id)
        if not stored:
            return False, "token not found"

        expected_sig = self._sign(stored)
        if not hmac.compare_digest(token.signature, expected_sig):
            return False, "invalid signature"

        identity = self._identities.get(token.agent_id)
        if not identity:
            return False, "agent not registered"

        if token.company != identity.company:
            return False, "token company mismatch"

        return True, "ok"

    def verify_request(
        self,
        agent_id: str,
        token: AgentToken,
        required_capability: str,
        resource_company: str,
    ) -> tuple[bool, str]:
        """Full verification: token valid, agent owns capability, company matches."""
        valid, reason = self.verify_token(token)
        if not valid:
            return False, reason

        if token.agent_id != agent_id:
            return False, "agent_id mismatch"

        if token.company != resource_company:
            return False, "cross-company access denied"

        if required_capability not in token.capabilities:
            return False, f"missing capability: {required_capability}"

        return True, "ok"

    def revoke_token(self, token_id: str) -> bool:
        if token_id in self._tokens:
            del self._tokens[token_id]
            return True
        return False

    def _sign(self, token: AgentToken) -> str:
        payload = f"{token.token_id}:{token.agent_id}:{token.task_id}:{token.company}:{token.expires_at}"
        return hmac.new(
            self._signing_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
