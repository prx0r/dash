"""Campaign audit: structure, traceability, gate honesty, opportunity rank."""

import re
from pathlib import Path

import pytest

CAMP_DIR = Path("/root/agentcom/campaigns")

with open("/root/agentcom/campaigns/BLUEPRINT.md") as f:
    pass  # blueprint exists (covered by file test below)

EXPECTED = [
    "CAMP-BARBER-GB", "CAMP-BEAUTY-GB", "CAMP-MEDSPA-GB", "CAMP-RESTAURANT-GB",
    "CAMP-HOTEL-GB", "CAMP-ELECTRICIAN-GB", "CAMP-HVAC-GB", "CAMP-GARAGE-GB",
    "CAMP-TREE-GB", "CAMP-BUILDER-GB", "CAMP-TUTOR-GB", "CAMP-CLEANING-GB",
    "CAMP-WINDOW-GB", "CAMP-FUNERAL-GB", "CAMP-VET-GB", "CAMP-MSP-GB",
    "CAMP-BOOKKEEPING-GB", "CAMP-DROPSHIP-GB", "CAMP-RESELLER-GB",
    "CAMP-RETAIL-GB", "CAMP-PETCARE-GB", "CAMP-GIG-GB",
    "CAMP-GP-GB", "CAMP-CARE-GB",
]

GATES = [f"G{i}" for i in range(1, 13)]


def read(cid):
    return (CAMP_DIR / f"{cid}.md").read_text()


def gates_of(text):
    return dict(re.findall(r"(G\d{1,2})\s+(PASS|FAIL|UNKNOWN)", text))


def verdict_of(text):
    m = re.search(r"Verdict:\s*(ELIGIBLE|BLOCKED|REJECTED|REROUTE)", text)
    return m.group(1) if m else None


def expected_verdict(gates):
    states = [gates.get(g, "MISSING") for g in GATES]
    if any(s == "FAIL" for s in states):
        return "REJECTED"
    if any(s in ("UNKNOWN", "MISSING") for s in states):
        return "BLOCKED"
    return "ELIGIBLE"


@pytest.fixture(params=EXPECTED)
def campaign(request):
    return request.param, read(request.param)


class TestCampaignFiles:
    def test_all_present(self):
        assert (CAMP_DIR / "BLUEPRINT.md").exists()
        for cid in EXPECTED:
            assert (CAMP_DIR / f"{cid}.md").exists(), cid

    def test_ten_sections(self, campaign):
        cid, text = campaign
        for i in range(1, 11):
            assert re.search(rf"^## {i}\.", text, re.M), f"{cid} missing §{i}"

    def test_traceability(self, campaign):
        cid, text = campaign
        assert "Template: tpl-" in text, cid
        assert "Teardown: td-" in text, cid
        assert "Pattern:" in text, cid
        assert "Evidence bindings" in text, cid

    def test_no_invented_numbers(self, campaign):
        cid, text = campaign
        # £/$ figures must appear only beside evidence bindings or TBD context;
        # enforce: every section-4/9 number either cited or TBD. Lightweight:
        # file must contain TBD: (honest unknowns) if it contains £/$
        if re.search(r"£\d|\$\d", text):
            assert "TBD" in text, f"{cid}: numbers without TBDs"


class TestGateHonesty:
    def test_twelve_gates_present(self, campaign):
        cid, text = campaign
        g = gates_of(text)
        assert len(g) == 12, f"{cid}: has {len(g)} gates"

    def test_verdict_follows_rubric(self, campaign):
        cid, text = campaign
        assert verdict_of(text) == expected_verdict(gates_of(text)), cid

    def test_no_false_eligible(self):
        for cid in EXPECTED:
            text = read(cid)
            if verdict_of(text) == "ELIGIBLE":
                assert all(v == "PASS" for v in gates_of(text).values()), cid

    def test_unknowns_acknowledged(self, campaign):
        cid, text = campaign
        g = gates_of(text)
        if any(v == "UNKNOWN" for v in g.values()):
            assert verdict_of(text) in ("BLOCKED", "REJECTED"), cid
