"""Evidence client tests — fake transport, no network."""

import pytest

from agentcom.kernel.evidence import (
    ONSClient, NomisClient, template_priority, SIC_TO_TEMPLATES)


def fake_fetch_factory(routes: dict):
    def fake(url: str):
        for prefix, payload in routes.items():
            if url.startswith(prefix):
                return payload
        raise AssertionError(f"unexpected URL: {url}")
    return fake


@pytest.fixture
def ons():
    routes = {
        "https://api.beta.ons.gov.uk/v1/datasets?limit=2&offset=0": {
            "items": [
                {"id": "cpih01", "title": "CPIH inflation"},
                {"id": "wellbeing-quarterly", "title": "Wellbeing"},
            ]
        },
        "https://api.beta.ons.gov.uk/v1/datasets?limit=100&offset=0": {
            "items": [
                {"id": "cpih01", "title": "CPIH inflation", "description": "prices"},
            ]
        },
        "https://api.beta.ons.gov.uk/v1/datasets/cpih01": {
            "id": "cpih01", "title": "CPIH inflation",
        },
    }
    return ONSClient(fetch=fake_fetch_factory(routes))


@pytest.fixture
def nomis():
    routes = {
        "https://www.nomisweb.co.uk/api/v01/dataset/NM_1_1.data.json": {
            "obs": [{"obs_value": "12345"}]
        },
    }

    def fake(url: str):
        for prefix, payload in routes.items():
            if url.startswith(prefix):
                return payload
        raise AssertionError(f"unexpected URL: {url}")

    return NomisClient(fetch=fake)


class TestONSClient:
    def test_list_datasets(self, ons):
        items = ons.list_datasets(limit=2)
        assert [d["id"] for d in items] == ["cpih01", "wellbeing-quarterly"]

    def test_search_datasets(self, ons):
        found = ons.search_datasets("inflation")
        assert [d["id"] for d in found] == ["cpih01"]

    def test_get_dataset(self, ons):
        assert ons.get_dataset("cpih01")["title"] == "CPIH inflation"


class TestNomisClient:
    def test_claimant_count(self, nomis):
        ev = nomis.claimant_count_latest()
        assert ev is not None
        assert ev.value == "12345"
        assert ev.dataset == "NM_1_1"
        assert "Nomis" in ev.source
        assert ev.retrieved_at > 0
        assert "england" in ev.metric  # never label broader geography than proven


class TestPriority:
    def test_ranking_follows_vacancy_weight(self):
        ranked = template_priority({"Q": 5090.0, "F": 2321.0, "R": 999.0})
        assert ranked[0][0] == "tpl-gp-gb"
        assert ranked[0][1] == 5090.0
        ids = [t for t, _ in ranked]
        assert "tpl-electrician-gb" in ids
        assert "tpl-hvac-gb" in ids

    def test_unmapped_sections_ignored(self):
        assert template_priority({"R": 5.0, "C": 3.0}) == []

    def test_templates_span_sections_sum(self):
        ranked = dict(template_priority({"G": 100.0, "I": 50.0}))
        assert ranked["tpl-restaurant-gb"] == 50.0

    def test_map_covers_all_templates(self):
        from agentcom.kernel.templates import TemplateRegistry
        known = {t for v in SIC_TO_TEMPLATES.values() for t in v}
        for tid in TemplateRegistry().list_ids():
            assert tid in known, f"{tid} has no SIC mapping"
