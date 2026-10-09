"""Weakpoint loop — propose as PROPOSED, promote on evidence, never delete."""
from __future__ import annotations

from typing import Any

from .seed import edge, node


def propose_pain(template_id: str, pain: str, mechanism: str,
                 evidence_refs: list[str], now: str, rank: int = 99) -> tuple[dict, list[dict]]:
    """Build (node, edges) for a candidate pain. Caller inserts via connect helpers.
    Rank 99 = unranked until human triages into the 1..N ladder."""
    from .seed import tpl_node_id, _tpl_short
    pid = f"PAIN_{_tpl_short(template_id)}_P{abs(hash(pain)) % 10000:04d}"
    n = node(pid, "pain",
             {"pain": pain, "rank": rank, "mechanism": mechanism,
              "evidence_refs": evidence_refs, "verification": "PROPOSED",
              "basis": "template-analysis"}, now)
    return n, [edge(f"E-{tpl_node_id(template_id)}-{pid}",
                    tpl_node_id(template_id), pid, "HAS_PAIN", now)]


def promote_update(dataset: str, project: str, node_id: str, now: str) -> str:
    """SQL to flip PROPOSED→VERIFIED (auditable UPDATE, never rewrite)."""
    return f"""UPDATE `{project}.{dataset}.graph_nodes`
SET properties_json = TO_JSON_STRING(JSON_SET(
      PARSE_JSON(properties_json), '$.verification', 'VERIFIED')),
    updated_at = TIMESTAMP '{now}'
WHERE node_id = '{node_id}'
  AND JSON_VALUE(properties_json, '$.verification') = 'PROPOSED'"""


def demote_update(dataset: str, project: str, node_id: str, reason: str,
                  now: str) -> str:
    reason_esc = reason.replace("'", "\\'")
    return f"""UPDATE `{project}.{dataset}.graph_nodes`
SET properties_json = TO_JSON_STRING(JSON_SET(
      JSON_SET(PARSE_JSON(properties_json), '$.verification', 'REJECTED'),
      '$.reject_reason', '{reason_esc}')),
    updated_at = TIMESTAMP '{now}'
WHERE node_id = '{node_id}'"""
