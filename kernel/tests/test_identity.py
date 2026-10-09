"""Integration test: Company Identity → Graph → Gate → Action.

Proves that every action is linked to a company ID, and the company ID
is the root node of the graph.
"""

import pytest

from agentcom.kernel.policy import PolicyEngine, Verdict, SideEffect
from agentcom.kernel.credentials import CredentialBroker
from agentcom.kernel.approvals import ApprovalSystem
from agentcom.kernel.audit import AuditLog, AuditAction
from agentcom.kernel.tasks import TaskEngine
from agentcom.kernel.capabilities import CapabilityGate, GateDecision
from agentcom.kernel.graph.identity import IdentityService
from agentcom.kernel.adapters.cmail_adapter import CmailAdapter


@pytest.fixture
def adapter():
    policy = PolicyEngine.default_policy()
    broker = CredentialBroker()
    approvals = ApprovalSystem()
    audit = AuditLog()
    tasks = TaskEngine()
    identity = IdentityService()
    gate = CapabilityGate(policy, broker, approvals, audit, tasks)
    return CmailAdapter(gate, broker, audit, tasks, identity)


class TestCompanyIdentity:
    """Company ID is the root node of the graph."""

    def test_create_company(self, adapter):
        company = adapter.create_company("Agentcom", "agent-commerce", "GB", "human:tom")
        assert company.company_id.startswith("COMP-")
        assert company.name == "Agentcom"
        assert company.vertical == "agent-commerce"
        assert company.country == "GB"
        assert company.principal == "human:tom"

    def test_company_id_is_stable(self, adapter):
        company = adapter.create_company("Test", "barber", "GB", "human:tom")
        retrieved = adapter.get_company(company.company_id)
        assert retrieved is not None
        assert retrieved.company_id == company.company_id

    def test_actions_link_to_company(self, adapter):
        company = adapter.create_company("Test", "barber", "GB", "human:tom")
        check = adapter.can_execute("name.cf_check", {"domain": "test.com"},
                                     company_id=company.company_id)
        assert check["company_id"] == company.company_id
        assert check["resource"].startswith(company.company_id)

    def test_actions_without_company_still_work(self, adapter):
        check = adapter.can_execute("name.cf_check", {"domain": "test.com"})
        assert check["allowed"] is True
        assert check["company_id"] is None

    def test_purchase_linked_to_company(self, adapter):
        company = adapter.create_company("Agentcom", "agent-commerce", "GB", "human:tom")
        check = adapter.can_execute("name.cf_purchase", {"domain": "pog.pet"},
                                     company_id=company.company_id)
        assert check["company_id"] == company.company_id
        assert "pog.pet" in check["resource"]
        assert check["decision"] == "HUMAN"  # needs approval

    def test_graph_structure(self, adapter):
        """Company is root, resources attach to it."""
        company = adapter.create_company("Agentcom", "agent-commerce", "GB", "human:tom")

        # Domain check — attaches to company
        check = adapter.can_execute("name.cf_check", {"domain": "agentcom.org"},
                                     company_id=company.company_id)
        assert check["resource"] == f"{company.company_id}/cloudflare/domain/agentcom.org"

        # Phone search — attaches to same company
        check = adapter.can_execute("name.phone_search", {"country": "GB"},
                                     company_id=company.company_id)
        assert check["resource"].startswith(company.company_id)

        # Social check — attaches to same company
        check = adapter.can_execute("name.social", {"name": "agentcom"},
                                     company_id=company.company_id)
        assert check["resource"].startswith(company.company_id)
