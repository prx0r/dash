"""Meta-graph — our own analysis as queryable graph data.

Loads templates + teardowns + fixes into any GraphStore. No new data
model: the nodes are template/pain/fix/pattern/compliance, the edges
are has-pain/fixed-by/in-pattern/requires.

Queries this unlocks that JSON files can't do alone:
- all pains in one pattern (e.g. every booking-led pain, ranked)
- which compliance requirements recur across verticals
- which stats back which pains (evidence trail per fix)
"""

from __future__ import annotations

from typing import Any

from ..graph import Entity, Edge

# Vertical → pattern. Kept here (not in template files) so the
# classification can evolve without touching 24 validated files.
VERTICAL_PATTERN: dict[str, str] = {
    "barber": "booking-led",
    "beauty": "booking-led",
    "medspa": "booking-led",
    "tutor": "booking-led",
    "electrician": "job-led",
    "hvac": "job-led",
    "builder": "job-led",
    "tree_surgeon": "job-led",
    "garage": "job-led",
    "cleaning": "round-led",
    "window_cleaner": "round-led",
    "care": "rota-led",
    "petcare": "rota-led",
    "dropship": "catalog-led",
    "reseller": "catalog-led",
    "retail": "shop-led",
    "it_helpdesk": "ticket-led",
    "gp_surgery": "triage-led",
    "vet": "booking-clinical",
    "funeral": "case-led",
    "hotel": "accommodation-led",
    "restaurant": "booking-pos",
    "bookkeeping": "retainer-led",
    "gig_driver": "worker-led",
}


def build_meta_graph(store: Any, templates: Any, teardowns: Any) -> dict[str, int]:
    """Load all analysis into the store. Returns node/edge counts."""
    counts = {"nodes": 0, "edges": 0}

    def add_entity(entity: Entity) -> None:
        store.add_entity(entity)
        counts["nodes"] += 1

    def add_edge(edge: Edge) -> None:
        store.add_edge(edge)
        counts["edges"] += 1

    patterns_seen: set[str] = set()

    for tpl in templates.load_all():
        tid = tpl.template_id
        vertical = tpl.vertical
        pattern = VERTICAL_PATTERN.get(vertical, "unclassified")

        add_entity(Entity(entity_id=f"template/{tid}", entity_type="template",
                          attributes={"vertical": vertical, "pattern": pattern},
                          source="registry"))
        if pattern not in patterns_seen:
            patterns_seen.add(pattern)
            add_entity(Entity(entity_id=f"pattern/{pattern}", entity_type="pattern",
                              attributes={}, source="meta"))
        add_edge(Edge(edge_id=f"e-{tid}-pattern", from_entity=f"template/{tid}",
                      to_entity=f"pattern/{pattern}", relation="in_pattern",
                      source="meta"))

    for td in teardowns.load_all():
        tid = td.template_id
        for pain in td.raw.get("pain_ranking", []):
            pain_id = f"pain/{tid}/{pain['rank']}"
            add_entity(Entity(
                entity_id=pain_id, entity_type="pain",
                attributes={"pain": pain["pain"], "rank": pain["rank"],
                            "why": pain.get("why", "")},
                source=f"teardown:{td.teardown_id}"))
            add_edge(Edge(edge_id=f"e-{pain_id}-tpl", from_entity=f"template/{tid}",
                          to_entity=pain_id, relation="has_pain", source="meta"))
            add_edge(Edge(edge_id=f"e-{pain_id}-fix", from_entity=pain_id,
                          to_entity=f"fix/{pain['fix_id']}", relation="fixed_by",
                          source="meta"))
        for leak in td.raw.get("margin_leaks", []):
            if leak.get("stat"):
                leak_id = f"leak/{tid}/{abs(hash(leak['name'])) % 10000:04d}"
                add_entity(Entity(
                    entity_id=leak_id, entity_type="stat",
                    attributes={"leak": leak["name"], "stat": leak["stat"],
                                "basis": leak.get("stat_basis", "")},
                    source=f"teardown:{td.teardown_id}"))
                add_edge(Edge(edge_id=f"e-{leak_id}-tpl", from_entity=f"template/{tid}",
                              to_entity=leak_id, relation="evidenced_by", source="meta"))
        for req in td.raw.get("compliance_spine", []):
            comp_id = f"compliance/{abs(hash(req['requirement'])) % 100000:05d}"
            if store.get_entity(comp_id) is None:
                add_entity(Entity(
                    entity_id=comp_id, entity_type="compliance",
                    attributes={"requirement": req["requirement"],
                                "source": req.get("source", "")},
                    source="meta"))
            add_edge(Edge(edge_id=f"e-{tid}-{comp_id[-5:]}-req",
                          from_entity=f"template/{tid}", to_entity=comp_id,
                          relation="requires", source="meta"))

    # Fix nodes (one per shared fix)
    import json as _json
    from pathlib import Path as _Path
    fixes_path = _Path(__file__).parent / "fixes.json"
    if fixes_path.exists():
        for fix in _json.loads(fixes_path.read_text()).get("fixes", []):
            add_entity(Entity(entity_id=f"fix/{fix['id']}", entity_type="fix",
                              attributes={"name": fix["name"]},
                              source="fixes.json"))

    return counts


def pains_in_pattern(store: Any, pattern: str) -> list[dict[str, Any]]:
    """Every pain in a pattern, with template + rank + fix."""
    out: list[dict[str, Any]] = []
    for edge in store.query_edges(relation="in_pattern", limit=1000):
        if edge.to_entity != f"pattern/{pattern}":
            continue
        tid = edge.from_entity.split("/", 1)[1]
        for pe in store.query_edges(from_entity=edge.from_entity,
                                    relation="has_pain", limit=50):
            pain = store.get_entity(pe.to_entity)
            if not pain:
                continue
            fix = ""
            for fe in store.query_edges(from_entity=pe.to_entity,
                                        relation="fixed_by", limit=5):
                fix = fe.to_entity
            out.append({"template": tid, "rank": pain.attributes.get("rank"),
                        "pain": pain.attributes.get("pain"), "fix": fix})
    out.sort(key=lambda r: (r["rank"] if isinstance(r["rank"], int) else 99,
                            r["template"]))
    return out


def compliance_recurrence(store: Any) -> list[tuple[str, int, list[str]]]:
    """Compliance requirements shared across templates: (requirement, count, templates)."""
    holders: dict[str, set[str]] = {}
    labels: dict[str, str] = {}
    for edge in store.query_edges(relation="requires", limit=2000):
        comp = store.get_entity(edge.to_entity)
        if not comp:
            continue
        req = comp.attributes.get("requirement", "")
        key = req.lower()
        holders.setdefault(key, set()).add(edge.from_entity)
        labels[key] = req
    ranked = sorted(((labels[k], len(v), sorted(t.split("/", 1)[1] for t in v))
                     for k, v in holders.items()),
                    key=lambda r: (-r[1], r[0]))
    return ranked


def stats_for_fix(store: Any, fix_id: str) -> list[dict[str, Any]]:
    """Every stat backing pains that a fix addresses (evidence trail)."""
    out: list[dict[str, Any]] = []
    pains = [e.from_entity for e in store.query_edges(
        to_entity=f"fix/{fix_id}", relation="fixed_by", limit=500)]
    pain_templates = {p: None for p in pains}
    for p in pains:
        for e in store.query_edges(to_entity=p, relation="has_pain", limit=5):
            pain_templates[p] = e.from_entity
    for p, tmpl in pain_templates.items():
        if not tmpl:
            continue
        for e in store.query_edges(from_entity=tmpl, relation="evidenced_by",
                                   limit=20):
            stat = store.get_entity(e.to_entity)
            if stat:
                out.append({"template": tmpl.split("/", 1)[1],
                            "leak": stat.attributes.get("leak"),
                            "stat": stat.attributes.get("stat"),
                            "basis": stat.attributes.get("basis")})
    return out
