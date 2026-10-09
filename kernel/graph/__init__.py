"""Storage Abstraction — GraphStore interface for D1/Postgres/SQLite.

Provides a consistent interface for entity storage. D1 today, Postgres later.
Relational tables + edges + events are adequate — no graph database needed.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """A node in the company graph."""
    entity_id: str
    entity_type: str  # company, person, resource, account, integration, credential_ref, policy
    attributes: dict[str, Any] = field(default_factory=dict)
    valid_from: float = field(default_factory=time.time)
    valid_to: float | None = None
    source: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class Edge:
    """A relationship between entities."""
    edge_id: str
    from_entity: str
    to_entity: str
    relation: str  # owns, manages, has_capability, bound_to, governed_by
    attributes: dict[str, Any] = field(default_factory=dict)
    valid_from: float = field(default_factory=time.time)
    valid_to: float | None = None
    source: str = ""


@dataclass
class Event:
    """An immutable event in the graph."""
    event_id: str
    entity_id: str
    event_type: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class GraphStore(ABC):
    """Abstract storage interface for the company graph."""

    @abstractmethod
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get a single entity by ID."""

    @abstractmethod
    def add_entity(self, entity: Entity) -> None:
        """Add a new entity."""

    @abstractmethod
    def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> None:
        """Update entity attributes (creates a new version)."""

    @abstractmethod
    def query_entities(
        self,
        entity_type: str | None = None,
        attributes: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Entity]:
        """Query entities by type and/or attributes."""

    @abstractmethod
    def add_edge(self, edge: Edge) -> None:
        """Add a relationship edge."""

    @abstractmethod
    def query_edges(
        self,
        from_entity: str | None = None,
        to_entity: str | None = None,
        relation: str | None = None,
        limit: int = 100,
    ) -> list[Edge]:
        """Query edges."""

    @abstractmethod
    def append_event(self, event: Event) -> None:
        """Append an immutable event."""

    @abstractmethod
    def query_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Query events."""

    @abstractmethod
    def snapshot(self, entity_id: str) -> dict[str, Any]:
        """Get current state of entity with all relationships."""


class InMemoryGraphStore(GraphStore):
    """In-memory implementation for testing."""

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._edges: list[Edge] = []
        self._events: list[Event] = []

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.entity_id] = entity

    def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> None:
        entity = self._entities.get(entity_id)
        if entity:
            entity.attributes.update(attributes)

    def query_entities(
        self,
        entity_type: str | None = None,
        attributes: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Entity]:
        results = list(self._entities.values())
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        if attributes:
            results = [e for e in results if all(e.attributes.get(k) == v for k, v in attributes.items())]
        return results[:limit]

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def query_edges(
        self,
        from_entity: str | None = None,
        to_entity: str | None = None,
        relation: str | None = None,
        limit: int = 100,
    ) -> list[Edge]:
        results = list(self._edges)
        if from_entity:
            results = [e for e in results if e.from_entity == from_entity]
        if to_entity:
            results = [e for e in results if e.to_entity == to_entity]
        if relation:
            results = [e for e in results if e.relation == relation]
        return results[:limit]

    def append_event(self, event: Event) -> None:
        self._events.append(event)

    def query_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[Event]:
        results = list(self._events)
        if entity_id:
            results = [e for e in results if e.entity_id == entity_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[:limit]

    def snapshot(self, entity_id: str) -> dict[str, Any]:
        entity = self._entities.get(entity_id)
        if not entity:
            return {}
        outgoing = [e for e in self._edges if e.from_entity == entity_id]
        incoming = [e for e in self._edges if e.to_entity == entity_id]
        events = [e for e in self._events if e.entity_id == entity_id]
        return {
            "entity": entity,
            "outgoing_edges": outgoing,
            "incoming_edges": incoming,
            "events": events,
        }
