"""FakeCloudflareRegistrar — simulated provider for testing.

Security tests should never use real provider APIs. This adapter
simulates Cloudflare Registrar operations with zero side effects.

Usage:
    from agentcom.kernel.adapters.fake_cloudflare import FakeCloudflareRegistrar

    fake = FakeCloudflareRegistrar()
    result = fake.purchase("agentcom.org")
    # → {"success": true, "domain": "agentcom.org", "charged": 0.0}
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeRegistration:
    domain: str
    registered_at: float
    expires_at: float
    state: str = "active"


class FakeCloudflareRegistrar:
    """Simulated Cloudflare Registrar. Zero real side effects.

    Every operation is recorded but nothing actually happens.
    No real money is charged. No real domain is registered.
    """

    def __init__(self):
        self._registrations: dict[str, FakeRegistration] = {}
        self._zones: dict[str, str] = {}  # domain → zone_id
        self._email_routing: dict[str, bool] = {}
        self._call_log: list[dict[str, Any]] = []

    def check(self, domain: str) -> dict[str, Any]:
        """Check domain availability. Always returns available unless already registered."""
        self._call_log.append({"action": "check", "domain": domain, "ts": time.time()})
        registered = domain in self._registrations
        return {
            "domain": domain,
            "registrable": not registered,
            "tier": "standard",
            "pricing": {
                "currency": "USD",
                "registration_cost": "8.50",
                "renewal_cost": "11.20",
            },
        }

    def purchase(self, domain: str, contact: dict[str, Any] | None = None) -> dict[str, Any]:
        """Simulate domain purchase. Records transaction, charges $0."""
        self._call_log.append({
            "action": "purchase",
            "domain": domain,
            "contact": contact,
            "ts": time.time(),
            "charged": 0.0,
        })

        if domain in self._registrations:
            return {
                "success": False,
                "error": f"Domain already registered: {domain}",
            }

        self._registrations[domain] = FakeRegistration(
            domain=domain,
            registered_at=time.time(),
            expires_at=time.time() + 365 * 86400,
        )

        return {
            "success": True,
            "state": "succeeded",
            "completed": True,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "domain": domain,
            "charged": 0.0,
            "note": "SIMULATED — no real domain registered, no real money charged",
        }

    def wire_email(self, domain: str, worker: str = "cmail") -> dict[str, Any]:
        """Simulate email routing setup."""
        self._call_log.append({
            "action": "wire_email",
            "domain": domain,
            "worker": worker,
            "ts": time.time(),
        })

        self._zones[domain] = "fake-zone-" + domain.replace(".", "-")
        self._email_routing[domain] = True

        return {
            "success": True,
            "domain": domain,
            "zone_id": self._zones[domain],
            "email_routing": True,
            "catch_all": True,
            "aliases": [f"{local}@{domain}" for local in ["hello", "support", "billing", "agents"]],
            "note": "SIMULATED — no real email routing configured",
        }

    def audit_log(self) -> list[dict[str, Any]]:
        """Return all simulated API calls."""
        return list(self._call_log)

    def reset(self) -> None:
        """Clear all simulated state."""
        self._registrations.clear()
        self._zones.clear()
        self._email_routing.clear()
        self._call_log.clear()
