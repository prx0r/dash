# Agentcom Kernel

Universal security primitives for agent commerce. The trust boundary between untrusted model-controlled execution and deterministic provider access.

## Architecture

```
            ChatGPT / OpenAI Agents
                     │
                     ▼
                AGENTCOM MCP
                     │
                     ▼
            ┌─────────────────┐
            │   ATask token   │
            └────────┬────────┘
                     ▼
          ╔══════════════════════╗
          ║  CAPABILITY GATE     ║
          ║                      ║
          ║ identity             ║
          ║ task scope           ║
          ║ resource scope       ║
          ║ policy               ║
          ║ budget               ║
          ║ parameter validation ║
          ║ approval             ║
          ╚════════╤═════════════╝
                   │
             ALLOW/HUMAN/DENY
                   │
                   ▼
           Credential Broker
                   │
                   ▼
            Provider Adapter
                   │
        Cloudflare/Telnyx/Meta
                   │
                   ▼
                Receipt
                   │
           ┌───────┴───────┐
           ▼               ▼
     CompanyGraph       AISec trace
```

## Invariant

**No model-controlled execution environment can retrieve a reusable credential.**

The model sees: `{"resource": "cloudflare/account/123", "capabilities": ["dns.write"]}`
The model never sees: the actual API key.

## Components

| Module | Purpose |
|--------|---------|
| `capabilities/` | Capability Gate — the trust boundary |
| `credentials/` | Credential Broker — injects keys internally |
| `policy/` | Policy Engine — per-resource, per-action rules, SideEffect 0-5 |
| `approvals/` | Approval System — parameter-bound, human-principal-only auth |
| `audit/` | Audit Log — immutable decision trail |
| `tasks/` | Task Engine — A-Task → M-Task/H-Task hierarchy |
| `graph/` | CompanyGraph — entity storage (D1/SQLite), identity, getsocials DAG |
| `adapters/` | Integration adapters (cmail, fake Cloudflare) |
| `schemas/` | JSON schemas: ATask, Approval, Template, Teardown, DistillOp |
| `templates/` | 24 vertical templates (graph shapes + stacks + workflows) |
| `teardowns/` | 24 business teardowns + meta-graph + pain index |
| `compliance/` | Legislation pack (basis-tagged) + regulators per vertical |
| `evidence/` | Keyless ONS/Nomis clients + SIC→template priority |
| `analysis/` | Pattern rollups, readiness, opportunity ranking |
| `bigquery/` | Loaders, metrics, decisions export, weakpoints, views |
| `distill/` | distillprotocol: 6 ops turning BQ sprawl into campaigns |
| `tests/` | Full suite (486 tests) |

## Task Hierarchy

```
A-GOAL
  │
  ▼
A-TASK
bounded unit of economic work
  │
  ├── M-TASK
  │   executable autonomously
  │
  └── H-TASK
      requires human action/authority
```

Every action belongs to an ATask. No orphaned actions.

## Quick Start

```python
from agentcom.kernel.policy import PolicyEngine
from agentcom.kernel.credentials import CredentialBroker
from agentcom.kernel.approvals import ApprovalSystem
from agentcom.kernel.audit import AuditLog
from agentcom.kernel.tasks import TaskEngine
from agentcom.kernel.capabilities import CapabilityGate

# Initialize
policy = PolicyEngine.default_policy()
broker = CredentialBroker()
approvals = ApprovalSystem()
audit = AuditLog()
tasks = TaskEngine()
gate = CapabilityGate(policy, broker, approvals, audit, tasks)

# Create an ATask
atask = tasks.create_atask(
    goal="Provision identity for EvSpark",
    principal="owner",
    agent="cmail",
    company="evspark",
    capabilities_required=["domain.check", "domain.purchase", "email.write"],
    approval_policy={
        "domain.check": "autonomous",
        "domain.purchase": "human_approval",
        "email.write": "autonomous",
    },
    money_budget={"amount": 15, "currency": "GBP"},
)

# Check a tool call
result = gate.check(
    action="domain.check",
    resource="cloudflare/domain/evspark.co.uk",
    task_id=atask.task_id,
    agent="cmail",
)
# result.decision → GateDecision.ALLOW

# Domain purchase needs approval
result = gate.check(
    action="domain.purchase",
    resource="cloudflare/domain/evspark.co.uk",
    task_id=atask.task_id,
    agent="cmail",
    amount=8.03,
)
# result.decision → GateDecision.HUMAN
```

## Security Regression Tests

```bash
python3 -m pytest agentcom/kernel/tests/ -q
```

486 tests: security regression, core invariant, self-authorization attack,
templates, teardowns, compliance, evidence, analysis, meta-graph, bigquery
loaders, blueprints, campaigns audit, distillprotocol, integration.

## Dual implementation note (read before refactoring)

Several packages contain BOTH a submodule implementation and a package-init
implementation with different APIs:

| Package `__init__` (canonical for new work) | Sibling module (original) |
|---|---|
| `policy` (SideEffect, Verdict) | `policy/engine.py` (Effect) |
| `capabilities` (GateDecision) | `capabilities/gate.py`, `broker.py` (GateVerdict) |
| `approvals` (human-principal-only) | `approvals/bind.py` (ApprovalService) |
| `audit` (AuditAction) | `audit/log.py` (AuditEvent) |
| `tasks` (M/H split) | `tasks/schema.py` |
| `graph` (GraphStore, identity, getsocials) | `graph/store.py`, `graph/schema.py` |
| auth surface | `auth/identity.py` |

`test_integration.py` (13 tests) exercises the sibling versions; everything
else exercises the package versions. BQ loaders, distill, templates and all
new work use the package versions — treat those as canonical. Do NOT delete
either side without instruction; consolidate deliberately, not casually.

## Design Decisions

1. **Kernel is the security root** — not `/ab`, not `/cmail`. Universal primitives.
2. **A-Task is atomic** — contains goal, authority, budget, scope, validator. No orphaned actions.
3. **Approvals are parameter-bound** — "buy agentbeauty.io for £10" cannot be reused for "malicious-domain.xyz".
4. **D1 for storage** — Cloudflare-native, matches cmail infrastructure. Storage abstraction allows Postgres later.
5. **Security tests in M0** — not M5. The regression suite ships with the kernel.
6. **Capability Gate is monolithic in V0** — one Worker/service, code/API boundary is the interface.

## File Structure

```
agentcom/kernel/
├── __init__.py
├── capabilities/
│   └── __init__.py          # Capability Gate
├── credentials/
│   └── __init__.py          # Credential Broker
├── policy/
│   └── __init__.py          # Policy Engine
├── approvals/
│   └── __init__.py          # Approval System
├── audit/
│   └── __init__.py          # Audit Log
├── tasks/
│   └── __init__.py          # Task Engine
├── graph/
│   ├── __init__.py          # GraphStore interface
│   └── d1.py               # D1/SQLite backend
├── adapters/
│   ├── __init__.py
│   └── cmail_adapter.py     # cmail MCP integration
├── schemas/
│   ├── atask.schema.v1.json
│   └── approval.schema.v1.json
└── tests/
    ├── __init__.py
    └── test_security.py     # 26 security regression tests
```
