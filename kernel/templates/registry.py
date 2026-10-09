"""Template registry — load, validate and apply vertical templates.

A template gives a company its graph shape after getsocials gives it
identity. Same security kernel, same getsocials procedure, different
nodes/edges/workflows per vertical.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).parent


@dataclass
class Template:
    template_id: str
    vertical: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def graph_shape(self) -> dict[str, Any]:
        return self.raw.get("graph_shape", {"nodes": [], "edges": []})

    @property
    def workflows(self) -> list[dict[str, Any]]:
        return self.raw.get("workflows", [])

    @property
    def canonical_stack(self) -> list[dict[str, Any]]:
        return self.raw.get("canonical_stack", [])

    @property
    def agentic_mapping(self) -> list[dict[str, Any]]:
        return self.raw.get("agentic_mapping", [])

    @property
    def extra_dag_steps(self) -> list[dict[str, Any]]:
        return self.raw.get("extra_dag_steps", [])

    @property
    def import_sources(self) -> list[str]:
        return self.raw.get("import_sources", [])

    @property
    def node_types(self) -> list[str]:
        return [n["entity_type"] for n in self.graph_shape.get("nodes", [])]


class TemplateRegistry:
    """Loads templates from disk, validates against schema, applies to graphs."""

    REQUIRED_KEYS = ("template_id", "vertical", "graph_shape", "workflows",
                     "canonical_stack", "agentic_mapping")

    def __init__(self, templates_dir: Path | None = None):
        self._dir = templates_dir or TEMPLATES_DIR
        self._cache: dict[str, Template] = {}

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("tpl-*.json"))

    def load(self, template_id: str) -> Template:
        if template_id in self._cache:
            return self._cache[template_id]
        path = self._dir / f"{template_id}.json"
        if not path.exists():
            raise KeyError(f"unknown template: {template_id}")
        raw = json.loads(path.read_text())
        self._validate(raw)
        tpl = Template(template_id=raw["template_id"], vertical=raw["vertical"], raw=raw)
        self._cache[template_id] = tpl
        return tpl

    def load_all(self) -> list[Template]:
        return [self.load(tid) for tid in self.list_ids()]

    def _validate(self, raw: dict[str, Any]) -> None:
        missing = [k for k in self.REQUIRED_KEYS if k not in raw]
        if missing:
            raise ValueError(f"template missing keys: {missing}")
        nodes = raw["graph_shape"].get("nodes", [])
        edges = raw["graph_shape"].get("edges", [])
        if not nodes:
            raise ValueError("template graph_shape.nodes is empty")
        node_types = {n["entity_type"] for n in nodes}
        for e in edges:
            if e["from"] not in node_types:
                raise ValueError(f"edge from unknown node: {e['from']}")
            if e["to"] not in node_types:
                raise ValueError(f"edge to unknown node: {e['to']}")
        for m in raw.get("agentic_mapping", []):
            if not m.get("retained", True) and not m.get("notes"):
                raise ValueError(
                    f"dropped function '{m.get('canonical_function')}' needs notes explaining why")

    def seed_graph(self, template_id: str, company_id: str, store: Any) -> dict[str, Any]:
        """Create empty template nodes under a company root. Returns counts.

        Works with any store exposing add_entity(Entity). Nodes are created
        empty (no field values) for FRESH path; IMPORT fills them later.
        """
        from ..graph import Entity
        import time

        tpl = self.load(template_id)
        created = 0
        for node in tpl.graph_shape.get("nodes", []):
            store.add_entity(Entity(
                entity_id=f"{company_id}/{tpl.vertical}/{node['entity_type']}",
                entity_type=node["entity_type"],
                attributes={"template": template_id, "seeded_at": time.time()},
                source=f"template:{template_id}",
            ))
            created += 1
        return {"template_id": template_id, "company_id": company_id,
                "nodes_created": created,
                "edges_defined": len(tpl.graph_shape.get("edges", []))}
