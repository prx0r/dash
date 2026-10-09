"""Company Identity — the root node of the graph.

Every company gets a stable ID from creation. All resources (domains,
emails, phones, socials, integrations) link back to this ID.

This is the foundation of the CompanyGraph. The ID persists across
all state transitions and is the canonical reference for every
action in the system.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompanyIdentity:
    """Canonical company identity. Immutable after creation."""
    company_id: str          # COMP-XXXXXXXX (stable, unique)
    name: str                # human-readable name
    vertical: str            # barber, plumber, electrician, etc.
    country: str             # GB, NO, FI, US, etc.
    principal: str           # who owns this company (human:*)
    created_at: float = field(default_factory=time.time)
    status: str = "active"   # active, suspended, archived
    attributes: dict[str, Any] = field(default_factory=dict)


class IdentityService:
    """Creates and manages company identities.

    The identity is the root node. Everything else is an edge.
    """

    def __init__(self):
        self._companies: dict[str, CompanyIdentity] = {}

    def create(
        self,
        name: str,
        vertical: str,
        country: str,
        principal: str,
        attributes: dict[str, Any] | None = None,
    ) -> CompanyIdentity:
        """Create a new company identity. Returns stable ID."""
        company_id = "COMP-" + secrets.token_hex(8).upper()
        company = CompanyIdentity(
            company_id=company_id,
            name=name,
            vertical=vertical,
            country=country,
            principal=principal,
            attributes=attributes or {},
        )
        self._companies[company_id] = company
        return company

    def get(self, company_id: str) -> CompanyIdentity | None:
        return self._companies.get(company_id)

    def list_all(self) -> list[CompanyIdentity]:
        return list(self._companies.values())

    def find_by_name(self, name: str) -> CompanyIdentity | None:
        for c in self._companies.values():
            if c.name.lower() == name.lower():
                return c
        return None

    def update_status(self, company_id: str, status: str) -> bool:
        company = self._companies.get(company_id)
        if company:
            company.status = status
            return True
        return False
