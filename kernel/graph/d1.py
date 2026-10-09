"""Storage Abstraction — D1/SQLite backend for the company graph."""

from __future__ import annotations

import json
import time
from typing import Any

from .graph import GraphStore, Entity, Edge, Event


class D1GraphStore(GraphStore):
    """D1-backed graph store. Falls back to SQLite for local dev."""

    def __init__(self, db: Any = None):
        self._db = db  # D1Database or sqlite3.Connection

    def get_entity(self, entity_id: str) -> Entity | None:
        if not self._db:
            return None
        row = self._db.execute(
            "SELECT entity_id, entity_type, attributes_json, valid_from, valid_to, source, created_at "
            "FROM entities WHERE entity_id = ?", (entity_id,)
        ).fetchone()
        if not row:
            return None
        return Entity(
            entity_id=row[0],
            entity_type=row[1],
            attributes=json.loads(row[2]) if row[2] else {},
            valid_from=row[3],
            valid_to=row[4],
            source=row[5],
            created_at=row[6],
        )

    def add_entity(self, entity: Entity) -> None:
        if not self._db:
            return
        self._db.execute(
            "INSERT OR REPLACE INTO entities (entity_id, entity_type, attributes_json, valid_from, valid_to, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (entity.entity_id, entity.entity_type, json.dumps(entity.attributes),
             entity.valid_from, entity.valid_to, entity.source, entity.created_at),
        )
        self._db.commit()

    def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> None:
        entity = self.get_entity(entity_id)
        if entity:
            entity.attributes.update(attributes)
            self.add_entity(entity)

    def query_entities(
        self,
        entity_type: str | None = None,
        attributes: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Entity]:
        if not self._db:
            return []
        if entity_type:
            rows = self._db.execute(
                "SELECT entity_id, entity_type, attributes_json, valid_from, valid_to, source, created_at "
                "FROM entities WHERE entity_type = ? LIMIT ?",
                (entity_type, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT entity_id, entity_type, attributes_json, valid_from, valid_to, source, created_at "
                "FROM entities LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            Entity(
                entity_id=r[0], entity_type=r[1],
                attributes=json.loads(r[2]) if r[2] else {},
                valid_from=r[3], valid_to=r[4], source=r[5], created_at=r[6],
            )
            for r in rows
        ]

    def add_edge(self, edge: Edge) -> None:
        if not self._db:
            return
        self._db.execute(
            "INSERT OR REPLACE INTO edges (edge_id, from_entity, to_entity, relation, attributes_json, valid_from, valid_to, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (edge.edge_id, edge.from_entity, edge.to_entity, edge.relation,
             json.dumps(edge.attributes), edge.valid_from, edge.valid_to, edge.source),
        )
        self._db.commit()

    def query_edges(
        self,
        from_entity: str | None = None,
        to_entity: str | None = None,
        relation: str | None = None,
        limit: int = 100,
    ) -> list[Edge]:
        if not self._db:
            return []
        conditions = []
        params = []
        if from_entity:
            conditions.append("from_entity = ?")
            params.append(from_entity)
        if to_entity:
            conditions.append("to_entity = ?")
            params.append(to_entity)
        if relation:
            conditions.append("relation = ?")
            params.append(relation)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self._db.execute(
            f"SELECT edge_id, from_entity, to_entity, relation, attributes_json, valid_from, valid_to, source "
            f"FROM edges WHERE {where} LIMIT ?",
            params,
        ).fetchall()
        return [
            Edge(
                edge_id=r[0], from_entity=r[1], to_entity=r[2], relation=r[3],
                attributes=json.loads(r[4]) if r[4] else {},
                valid_from=r[5], valid_to=r[6], source=r[7],
            )
            for r in rows
        ]

    def append_event(self, event: Event) -> None:
        if not self._db:
            return
        self._db.execute(
            "INSERT INTO events (event_id, entity_id, event_type, details_json, timestamp, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.entity_id, event.event_type,
             json.dumps(event.details), event.timestamp, event.source),
        )
        self._db.commit()

    def query_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[Event]:
        if not self._db:
            return []
        conditions = []
        params = []
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self._db.execute(
            f"SELECT event_id, entity_id, event_type, details_json, timestamp, source "
            f"FROM events WHERE {where} LIMIT ?",
            params,
        ).fetchall()
        return [
            Event(
                event_id=r[0], entity_id=r[1], event_type=r[2],
                details=json.loads(r[3]) if r[3] else {},
                timestamp=r[4], source=r[5],
            )
            for r in rows
        ]

    def snapshot(self, entity_id: str) -> dict[str, Any]:
        entity = self.get_entity(entity_id)
        if not entity:
            return {}
        outgoing = self.query_edges(from_entity=entity_id)
        incoming = self.query_edges(to_entity=entity_id)
        events = self.query_events(entity_id=entity_id)
        return {
            "entity": entity,
            "outgoing_edges": outgoing,
            "incoming_edges": incoming,
            "events": events,
        }


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    valid_from REAL NOT NULL,
    valid_to REAL,
    source TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

CREATE TABLE IF NOT EXISTS edges (
    edge_id TEXT PRIMARY KEY,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    relation TEXT NOT NULL,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    valid_from REAL NOT NULL,
    valid_to REAL,
    source TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_entity);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_entity);
CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    timestamp REAL NOT NULL,
    source TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
"""
