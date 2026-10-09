"""Agentcom Kernel — universal security primitives for agent commerce.

The kernel is the trust boundary between untrusted model-controlled execution
and deterministic provider access. No model-controlled environment can retrieve
a reusable credential.

Architecture:
    agent → Agentcom MCP → Capability Gate → Policy → Credential Broker → Provider
                                      ↓
                               Audit + Receipts
"""

__version__ = "0.1.0"
