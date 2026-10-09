"""Templates: validity + kernel integration.

Every template must satisfy the schema contract, reference only nodes it
defines, justify every dropped function, and seed a graph cleanly.
"""

import pytest

from agentcom.kernel.templates import TemplateRegistry
from agentcom.kernel.graph import InMemoryGraphStore


@pytest.fixture
def registry():
    return TemplateRegistry()


@pytest.fixture
def store():
    return InMemoryGraphStore()


EXPECTED_TEMPLATES = [
    "tpl-barber-gb",
    "tpl-beauty-gb",
    "tpl-electrician-gb",
    "tpl-garage-gb",
    "tpl-dropship-gb",
    "tpl-msp-gb",
    "tpl-hvac-gb",
    "tpl-cleaning-gb",
    "tpl-medspa-gb",
    "tpl-gp-gb",
    "tpl-funeral-gb",
    "tpl-restaurant-gb",
    "tpl-reseller-gb",
    "tpl-gig-driver-gb",
    "tpl-petcare-gb",
    "tpl-bookkeeping-gb",
    "tpl-vet-gb",
    "tpl-hotel-gb",
    "tpl-tree-surgeon-gb",
    "tpl-window-cleaner-gb",
    "tpl-tutor-gb",
    "tpl-retail-gb",
    "tpl-care-gb",
    "tpl-builder-gb",
]


class TestTemplateRegistry:
    def test_all_expected_templates_exist(self, registry):
        assert registry.list_ids() == sorted(EXPECTED_TEMPLATES)

    def test_every_template_loads(self, registry):
        for tid in EXPECTED_TEMPLATES:
            tpl = registry.load(tid)
            assert tpl.template_id == tid

    def test_unknown_template_raises(self, registry):
        with pytest.raises(KeyError):
            registry.load("tpl-nope-gb")


class TestTemplateValidity:
    @pytest.mark.parametrize("tid", EXPECTED_TEMPLATES)
    def test_has_nodes_and_edges(self, registry, tid):
        tpl = registry.load(tid)
        assert len(tpl.graph_shape["nodes"]) >= 3
        assert len(tpl.graph_shape["edges"]) >= 3

    @pytest.mark.parametrize("tid", EXPECTED_TEMPLATES)
    def test_edges_reference_known_nodes(self, registry, tid):
        tpl = registry.load(tid)
        known = set(tpl.node_types)
        for e in tpl.graph_shape["edges"]:
            assert e["from"] in known, f"{tid}: edge from unknown {e['from']}"
            assert e["to"] in known, f"{tid}: edge to unknown {e['to']}"

    @pytest.mark.parametrize("tid", EXPECTED_TEMPLATES)
    def test_canonical_stack_has_verdicts(self, registry, tid):
        tpl = registry.load(tid)
        assert len(tpl.canonical_stack) >= 3
        for tool in tpl.canonical_stack:
            assert tool["verdict"] in ("replace", "integrate", "import-from")

    @pytest.mark.parametrize("tid", EXPECTED_TEMPLATES)
    def test_dropped_functions_justified(self, registry, tid):
        tpl = registry.load(tid)
        for m in tpl.agentic_mapping:
            assert m["retained"] is True or m.get("notes"), \
                f"{tid}: dropped '{m['canonical_function']}' without justification"

    @pytest.mark.parametrize("tid", EXPECTED_TEMPLATES)
    def test_has_workflows(self, registry, tid):
        tpl = registry.load(tid)
        assert len(tpl.workflows) >= 1
        for w in tpl.workflows:
            assert w["trigger"] and len(w["steps"]) >= 2


class TestTemplateGraphIntegration:
    @pytest.mark.parametrize("tid", EXPECTED_TEMPLATES)
    def test_seed_graph_creates_nodes(self, registry, store, tid):
        result = registry.seed_graph(tid, "COMP-TEST", store)
        assert result["nodes_created"] >= 3
        tpl = registry.load(tid)
        for node_type in tpl.node_types:
            entity = store.get_entity(f"COMP-TEST/{tpl.vertical}/{node_type}")
            assert entity is not None
            assert entity.attributes["template"] == tid

    def test_two_companies_do_not_collide(self, registry, store):
        registry.seed_graph("tpl-barber-gb", "COMP-A", store)
        registry.seed_graph("tpl-barber-gb", "COMP-B", store)
        assert store.get_entity("COMP-A/barber/client") is not None
        assert store.get_entity("COMP-B/barber/client") is not None
        assert store.get_entity("COMP-A/barber/client") is not \
            store.get_entity("COMP-B/barber/client")

    def test_getsocials_root_links_to_template_nodes(self, registry, store):
        from agentcom.kernel.graph import Entity, Edge
        store.add_entity(Entity(entity_id="COMP-X", entity_type="company",
                               attributes={"name": "X"}, source="identity.create"))
        registry.seed_graph("tpl-garage-gb", "COMP-X", store)
        store.add_edge(Edge(edge_id="E-root", from_entity="COMP-X",
                            to_entity="COMP-X/garage/vehicle",
                            relation="shaped_by", source="template:tpl-garage-gb"))
        snap = store.snapshot("COMP-X")
        assert len(snap["outgoing_edges"]) == 1
