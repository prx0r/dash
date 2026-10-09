"""GraphStore — D1-backed company graph.

V0: in-memory implementation with the same interface.
Production: D1 tables.

Interface:
  get(), query(), add_entity(), update_entity(),
  add_edge(), append_event(), transaction(), snapshot()
"""
from __future__ import annotations

from typing import Any

from .schema import Edge, Entity, GraphEvent


class GraphStore:
    """Company graph storage.

    V0: in-memory. Swap to D1 when deploying.
    The storage interface is stable regardless of backend.
    """

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._edges: dict[str, Edge] = {}
        self._events: list[GraphEvent] = []

    def get(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def query(
        self,
        entity_type: str | None = None,
        company_id: str | None = None,
        name: str | None = None,
        valid_only: bool = True,
    ) -> list[Entity]:
        results = list(self._entities.values())
        if entity_type:
            results = [e for e in results if e.entity_type.value == entity_type]
        if company_id:
            results = [e for e in results if e.data.get("company_id") == company_id]
        if name:
            results = [e for e in results if e.name == name]
        if valid_only:
            results = [e for e in results if e.is_valid()]
        return results

    def add_entity(self, entity: Entity) -> Entity:
        self._entities[entity.entity_id] = entity
        self.append_event(
            event_type="entity.created",
            entity_id=entity.entity_id,
            data={"type": entity.entity_type.value, "name": entity.name},
        )
        return entity

    def update_entity(self, entity_id: str, data: dict[str, Any]) -> Entity | None:
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        entity.data.update(data)
        entity.updated_at = __import__("time").time()
        self.append_event(
            event_type="entity.updated",
            entity_id=entity_id,
            data=data,
        )
        return entity

    def add_edge(self, edge: Edge) -> Edge:
        self._edges[edge.edge_id] = edge
        self.append_event(
            event_type="edge.added",
            entity_id=edge.from_id,
            data={"to": edge.to_id, "relation": edge.relation},
        )
        return edge

    def get_edges(
        self,
        from_id: str | None = None,
        to_id: str | None = None,
        relation: str | None = None,
        valid_only: bool = True,
    ) -> list[Edge]:
        results = list(self._edges.values())
        if from_id:
            results = [e for e in results if e.from_id == from_id]
        if to_id:
            results = [e for e in results if e.to_id == to_id]
        if relation:
            results = [e for e in results if e.relation == relation]
        if valid_only:
            results = [e for e in results if e.is_valid()]
        return results

    def append_event(
        self,
        event_type: str,
        entity_id: str = "",
        actor: str = "",
        data: dict[str, Any] | None = None,
    ) -> GraphEvent:
        event = GraphEvent(
            event_type=event_type,
            entity_id=entity_id,
            actor=actor,
            data=data or {},
        )
        self._events.append(event)
        return event

    def get_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[GraphEvent]:
        results = self._events
        if entity_id:
            results = [e for e in results if e.entity_id == entity_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def snapshot(self, company_id: str) -> dict[str, Any]:
        """Return full state for a company."""
        # Include the company entity itself + entities belonging to it
        company_entity = self._entities.get(company_id)
        entities = [company_entity] if company_entity else []
        entities += [
            e for e in self._entities.values()
            if e.entity_id != company_id and e.data.get("company_id") == company_id
        ]
        entity_ids = {e.entity_id for e in entities}
        edges = [
            e for e in self._edges.values()
            if e.from_id in entity_ids or e.to_id in entity_ids
        ]
        events = [
            e for e in self._events
            if e.entity_id in entity_ids
        ]
        return {
            "company_id": company_id,
            "entities": [
                {
                    "id": e.entity_id,
                    "type": e.entity_type.value,
                    "name": e.name,
                    "data": e.data,
                    "valid": e.is_valid(),
                }
                for e in entities
            ],
            "edges": [
                {
                    "from": e.from_id,
                    "to": e.to_id,
                    "relation": e.relation,
                    "data": e.data,
                }
                for e in edges
            ],
            "events": [
                {
                    "id": e.event_id,
                    "type": e.event_type,
                    "entity": e.entity_id,
                    "actor": e.actor,
                    "data": e.data,
                    "timestamp": e.timestamp,
                }
                for e in events
            ],
        }

    def transaction(self, ops: list[dict[str, Any]]) -> list[Any]:
        """Execute multiple operations atomically. V0: sequential."""
        results = []
        for op in ops:
            kind = op.get("op")
            if kind == "add_entity":
                results.append(self.add_entity(op["entity"]))
            elif kind == "add_edge":
                results.append(self.add_edge(op["edge"]))
            elif kind == "update_entity":
                results.append(self.update_entity(op["entity_id"], op["data"]))
            else:
                raise ValueError(f"unknown op: {kind}")
        return results
