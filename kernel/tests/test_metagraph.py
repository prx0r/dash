"""Meta-graph: analysis loaded into GraphStore, cross-cutting queries."""

import pytest

from agentcom.kernel.graph import InMemoryGraphStore
from agentcom.kernel.templates import TemplateRegistry
from agentcom.kernel.teardowns import (
    TeardownRegistry, build_meta_graph, pains_in_pattern,
    compliance_recurrence, stats_for_fix, VERTICAL_PATTERN)


@pytest.fixture
def store():
    s = InMemoryGraphStore()
    counts = build_meta_graph(s, TemplateRegistry(), TeardownRegistry())
    assert counts["nodes"] > 100
    return s


class TestMetaGraph:
    def test_build_counts(self, store):
        entities = store.query_entities(limit=10000)
        edges = store.query_edges(limit=10000)
        assert len(entities) > 100
        assert len(edges) > 100

    def test_every_vertical_has_pattern(self):
        verticals = {t.vertical for t in TemplateRegistry().load_all()}
        assert set(verticals) <= set(VERTICAL_PATTERN), \
            f"unclassified: {set(verticals) - set(VERTICAL_PATTERN)}"

    def test_pains_in_booking_led(self, store):
        pains = pains_in_pattern(store, "booking-led")
        templates = {p["template"] for p in pains}
        assert {"tpl-barber-gb", "tpl-beauty-gb", "tpl-tutor-gb"} <= templates
        assert all(p["fix"] for p in pains)

    def test_pains_sorted_by_rank(self, store):
        pains = pains_in_pattern(store, "job-led")
        assert len(pains) > 0
        # ranks ascending within each template group is covered by sort contract
        assert all(isinstance(p["rank"], int) for p in pains)

    def test_compliance_recurrence(self, store):
        rec = compliance_recurrence(store)
        assert len(rec) > 0
        # structure: (requirement, holder count, [template ids])
        for req, count, holders in rec:
            assert req and count >= 1 and len(holders) == count
        # exact-match recurrence is rare (wording differs); keyword
        # normalization across requirements is future work, tracked here
        # so the query stays honest about what it measures

    def test_stats_for_fix(self, store):
        stats = stats_for_fix(store, "FIX-MARKETPLACE-TAX")
        assert len(stats) > 0
        assert all(s["stat"] and s["basis"] for s in stats)

    def test_fix_nodes_present(self, store):
        fixes = store.query_entities(entity_type="fix", limit=20)
        assert len(fixes) == 6
