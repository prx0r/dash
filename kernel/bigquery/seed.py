"""BigQuery loaders — kernel registries → drop.* rows.

Conventions (BIGQUERY_GRAPH_PLAN.md §1):
- Same three tables, new namespaces. properties_json is STRING (json.dumps).
- Idempotent: MERGE on node_id; edges check-then-insert on edge_id.
- Every row carries source=<loader>:v0.1 + confidence.
- Row builders are pure (dicts in, dicts out); only execute() touches BQ,
  so unit tests use a fake client and never touch the network.
"""
from __future__ import annotations

import datetime
import json
from typing import Any


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.upper()).strip("_")


def tpl_node_id(template_id: str) -> str:
    return _slug(template_id).replace("TPL_", "TPL_", 1) if template_id.startswith("tpl-") \
        else "TPL_" + _slug(template_id)


def _fix_id(raw_id: str) -> str:
    """FIX-NOSHOW in, FIX-NOSHOW out. Never FIX_FIX- anything."""
    return raw_id if raw_id.startswith("FIX-") else "FIX-" + _slug(raw_id)


def _law_id(raw_id: str) -> str:
    base = raw_id
    for prefix in ("LEG-", "LEG_", "LAW-", "LAW_"):
        if base.startswith(prefix):
            base = base[len(prefix):]
            break
    return "LAW_" + _slug(base)


def _tpl_short(template_id: str) -> str:
    short = template_id
    if short.startswith("tpl-"):
        short = short[4:]
    if short.endswith("-gb"):
        short = short[:-3]
    return _slug(short)


def node(node_id: str, node_type: str, properties: dict[str, Any], now: str,
         confidence: float | None = 1.0, source: str = "kernel-seed:v0.1") -> dict[str, Any]:
    return {"node_id": node_id, "node_type": node_type,
            "properties_json": json.dumps(properties), "created_at": now,
            "updated_at": now, "confidence": confidence, "source": source}


def edge(edge_id: str, source_node: str, target_node: str, edge_type: str,
         now: str, weight: float = 1.0,
         source: str = "kernel-seed:v0.1") -> dict[str, Any]:
    return {"edge_id": edge_id, "source_node": source_node,
            "target_node": target_node, "edge_type": edge_type,
            "weight": weight, "created_at": now, "source": source}


def observation(node_id: str, metric_name: str, metric_value: float | None,
                now: str, evidence_type: str = "kernel-seed",
                source: str = "kernel-seed:v0.1") -> dict[str, Any]:
    import hashlib
    oid = "OBS-" + hashlib.sha256(
        f"{node_id}|{metric_name}|{now}".encode()).hexdigest()[:16].upper()
    return {"observation_id": oid, "node_id": node_id, "observed_at": now,
            "metric_name": metric_name, "metric_value": metric_value,
            "evidence_type": evidence_type, "source": source}


def build_template_rows(tpl: Any, now: str) -> tuple[list[dict], list[dict]]:
    """Nodes: TPL_*, VERT_* (+IN_PATTERN edge needs pattern — caller adds);
    TOOL_* nodes + USES_STACK edges. Returns (nodes, edges)."""
    tid = tpl_node_id(tpl.template_id)
    nodes = [node(tid, "template",
                  {"template_id": tpl.template_id, "vertical": tpl.vertical,
                   "countries": tpl.raw.get("countries", []),
                   "entry_question": tpl.raw.get("entry_question", ""),
                   "import_sources": tpl.raw.get("import_sources", []),
                   "workflows": [w.get("name", "") for w in tpl.workflows],
                   "verification": "VERIFIED", "basis": "template-analysis"},
                  now)]
    edges: list[dict] = []
    vert_id = "VERT_" + _slug(tpl.vertical)
    nodes.append(node(vert_id, "vertical", {"vertical": tpl.vertical,
                                            "verification": "VERIFIED",
                                            "basis": "template-analysis"}, now))
    for tool in tpl.canonical_stack:
        tool_id = "TOOL_" + _slug(tool.get("tool", "unknown"))[:40]
        nodes.append(node(tool_id, "stack_tool",
                          {"tool": tool.get("tool", ""), "category": tool.get("category", ""),
                           "does": tool.get("does", "")[:500],
                           "verdict": tool.get("verdict", ""),
                           "verification": "VERIFIED", "basis": "verified-2026"}, now))
        edges.append(edge(f"E-{tid}-{tool_id}", tid, tool_id, "USES_STACK", now))
    return nodes, edges


def build_pattern_rows(pattern: str, now: str) -> list[dict]:
    return [node("PAT_" + _slug(pattern), "pattern", {"pattern": pattern,
             "verification": "VERIFIED", "basis": "template-analysis"}, now)]


def build_pattern_edge(template_id: str, pattern: str, now: str) -> dict:
    return edge(f"E-{tpl_node_id(template_id)}-PAT", tpl_node_id(template_id),
                "PAT_" + _slug(pattern), "IN_PATTERN", now)


def build_teardown_rows(td: Any, now: str) -> tuple[list[dict], list[dict], list[dict]]:
    """PAIN_* nodes + HAS_PAIN/FIXED_BY edges + numeric stat observations."""
    tid = tpl_node_id(td.template_id)
    short = _tpl_short(td.template_id)
    nodes, edges, observations = [], [], []
    for pain in td.raw.get("pain_ranking", []):
        pid = f"PAIN_{short}_{pain['rank']:02d}"
        nodes.append(node(pid, "pain",
                          {"pain": pain["pain"], "rank": pain["rank"],
                           "why": pain.get("why", ""), "fix_id": pain["fix_id"],
                           "verification": "VERIFIED", "basis": "template-analysis"},
                          now))
        edges.append(edge(f"E-{tid}-{pid}", tid, pid, "HAS_PAIN", now))
        edges.append(edge(f"E-{pid}-FIX", pid, _fix_id(pain["fix_id"]), "FIXED_BY", now))
    for leak in td.raw.get("margin_leaks", []):
        stat = leak.get("stat")
        num = _first_number(stat) if stat else None
        if num is not None:
            observations.append(observation(
                tid, f"leak.{_slug(leak['name'])[:40].lower()}", num, now,
                evidence_type=f"teardown:{td.teardown_id}"))
    return nodes, edges, observations


def _first_number(s: str) -> float | None:
    import re
    m = re.search(r"(\d+(?:\.\d+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else None


def build_fix_rows(fixes: list[dict[str, Any]], now: str) -> list[dict]:
    return [node(_fix_id(f["id"]), "fix",
                 {"name": f["name"], "description": f.get("description", ""),
                  "verification": "VERIFIED", "basis": "template-analysis"}, now)
            for f in fixes]


def build_legislation_rows(entries: list[Any], now: str) -> tuple[list[dict], list[dict]]:
    """LAW_* nodes. NONLAW_* entries become design-rule properties, not nodes."""
    nodes, edges = [], []
    for e in entries:
        raw = e.raw if hasattr(e, "raw") else e
        if raw.get("id", "").startswith("NONLAW-"):
            continue
        lid = _law_id(raw["id"])
        nodes.append(node(lid, "legislation",
                          {"law": raw.get("law", ""), "citation": raw.get("citation", ""),
                           "basis": raw.get("basis", ""),
                           "requires": raw.get("requires", []),
                           "source_url": raw.get("source_url", ""),
                           "verification": "VERIFIED"
                           if raw.get("basis") == "verified-2026" else "PROPOSED"},
                          now))
    return nodes, edges


def build_governed_edges(tpl_vertical: str, template_id: str,
                         legislation: list[Any], now: str) -> list[dict]:
    """GOVERNED_BY edges: template → laws covering its vertical."""
    tid = tpl_node_id(template_id)
    edges = []
    for e in legislation:
        raw = e.raw if hasattr(e, "raw") else e
        if raw.get("id", "").startswith("NONLAW-"):
            continue
        if tpl_vertical in raw.get("verticals", []):
            lid = _law_id(raw["id"])
            edges.append(edge(f"E-{tid}-{lid}", tid, lid, "GOVERNED_BY", now))
    return edges
