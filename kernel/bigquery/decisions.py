"""Kernel audit → BigQuery. D1 hot, BQ truth, fail-closed locally."""
from __future__ import annotations

AGENT_DECISIONS_DDL = """CREATE TABLE IF NOT EXISTS `{project}.{dataset}.agent_decisions` (
  decision_id STRING NOT NULL,
  decided_at TIMESTAMP NOT NULL,
  actor STRING NOT NULL,
  company_id STRING,
  task_id STRING,
  action STRING NOT NULL,
  resource STRING NOT NULL,
  decision STRING NOT NULL,
  reason STRING,
  approval_id STRING,
  side_effect INT64
)
PARTITION BY DATE(decided_at)
CLUSTER BY company_id, decision, action"""


def ensure_agent_decisions(client: Any, dataset: str) -> None:
    if hasattr(client, "_fake"):
        client._calls.append(("ensure_agent_decisions", dataset, []))
        return
    client.query(AGENT_DECISIONS_DDL.format(
        project=client.project, dataset=dataset)).result()


def audit_entry_to_row(entry: Any, now: str) -> dict | None:
    """Map one kernel AuditLog entry → agent_decisions row. None = not a decision."""
    decision = (entry.decision or "").upper()
    if decision not in ("ALLOW", "DENY", "HUMAN"):
        return None
    details = entry.details if isinstance(entry.details, dict) else {}
    return {"decision_id": entry.entry_id, "decided_at": now,
            "actor": entry.actor, "company_id": details.get("company_id"),
            "task_id": entry.task_id, "action": details.get("action", ""),
            "resource": entry.resource or "",
            "decision": decision, "reason": entry.reason,
            "approval_id": details.get("approval_id"),
            "side_effect": details.get("side_effect")}


def export_audit(client: Any, dataset: str, entries: list[Any], now: str) -> int:
    """Append decision entries. Raises on error — caller decides retry policy.
    The gate never blocks on export failure (fail-closed locally, sync later)."""
    rows = [r for r in (audit_entry_to_row(e, now) for e in entries) if r]
    if not rows:
        return 0
    if hasattr(client, "_fake"):
        client._calls.append(("export_audit", dataset, rows))
        return len(rows)
    errors = client.insert_rows_json(
        f"{client.project}.{dataset}.agent_decisions", rows)
    if errors:
        raise RuntimeError(f"agent_decisions insert errors: {errors[:3]}")
    return len(rows)
