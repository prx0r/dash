"""CompanyGraph entity schema.

Canonical company state. Temporal validity. Every fact has source.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    COMPANY = "company"
    PERSON = "person"
    RESOURCE = "resource"
    CREDENTIAL_REF = "credential_ref"
    INTEGRATION = "integration"
    POLICY = "policy"
    EVENT = "event"


class ResourceKind(str, Enum):
    DOMAIN = "domain"
    EMAIL = "email"
    PHONE = "phone"
    SOCIAL = "social"
    DNS = "dns"
    API_KEY = "api_key"
    WEBSITE = "website"


@dataclass
class Entity:
    """A graph entity with temporal validity."""
    entity_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_type: EntityType = EntityType.COMPANY
    name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    valid_from: float = field(default_factory=time.time)
    valid_to: float | None = None
    source: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def is_valid(self) -> bool:
        now = time.time()
        if now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True


@dataclass
class Edge:
    """A relationship between two entities."""
    edge_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_id: str = ""
    to_id: str = ""
    relation: str = ""  # e.g. "owns", "manages", "has_capability", "bound_to"
    data: dict[str, Any] = field(default_factory=dict)
    valid_from: float = field(default_factory=time.time)
    valid_to: float | None = None

    def is_valid(self) -> bool:
        now = time.time()
        if now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True


@dataclass
class GraphEvent:
    """An immutable event in the company graph."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""  # e.g. "entity.created", "edge.added", "credential.injected"
    entity_id: str = ""
    actor: str = ""  # agent_id or "human"
    data: dict[str, Any] = field(default_factory=dict)


# ---- Convenience constructors ----

def make_company(entity_id: str, name: str, country: str = "GB", **kwargs: Any) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type=EntityType.COMPANY,
        name=name,
        data={"country": country, **kwargs},
    )


def make_resource(
    entity_id: str,
    name: str,
    kind: ResourceKind,
    company_id: str,
    **kwargs: Any,
) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type=EntityType.RESOURCE,
        name=name,
        data={"kind": kind.value, "company_id": company_id, **kwargs},
    )


def make_credential_ref(
    entity_id: str,
    vault_path: str,
    provider: str,
    capabilities: list[str],
    company_id: str,
) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type=EntityType.CREDENTIAL_REF,
        name=vault_path,
        data={
            "vault_path": vault_path,
            "provider": provider,
            "capabilities": capabilities,
            "company_id": company_id,
            "exposure_policy": "never",
        },
    )


def make_integration(
    entity_id: str,
    provider: str,
    company_id: str,
    capabilities: list[str],
    status: str = "active",
    **kwargs: Any,
) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type=EntityType.INTEGRATION,
        name=provider,
        data={
            "provider": provider,
            "company_id": company_id,
            "capabilities": capabilities,
            "status": status,
            **kwargs,
        },
    )
