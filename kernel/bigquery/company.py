"""Company seeding — COMP_* root + getsocials progress observations."""
from __future__ import annotations

from typing import Any

from .seed import edge, node, observation


def company_node(company_id: str, name: str, vertical: str, country: str,
                 template_id: str, now: str) -> tuple[dict, dict]:
    """COMP_* root + SEEDED_FROM edge to its template. Company ids arrive as
    COMP-XXXXXXXX (kernel); BQ form is COMP_XXXXXXXX."""
    bq_id = "COMP_" + company_id.replace("COMP-", "").replace("-", "_").upper()
    n = node(bq_id, "company",
             {"name": name, "vertical": vertical, "country": country,
              "template_id": template_id, "status": "active",
              "verification": "VERIFIED", "basis": "kernel-identity"}, now)
    from .seed import tpl_node_id
    e = edge(f"E-{bq_id}-SEED", bq_id, tpl_node_id(template_id),
             "SEEDED_FROM", now)
    return n, e


def operates_in_edge(company_bq_id: str, country_code: str, now: str) -> dict:
    """COMP_* → COUNTRY_* using the existing country nodes (NO/GB/FI/…)."""
    return edge(f"E-{company_bq_id}-CO", company_bq_id, f"COUNTRY_{country_code}",
                "OPERATES_IN", now)


def getsocials_progress(company_bq_id: str, progress: dict[str, Any],
                        now: str) -> list[dict]:
    """Progress snapshot → observations (history lives here, not in node edits)."""
    out = [observation(company_bq_id, "getsocials.progress_pct",
                       float(str(progress.get("progress_pct", "0%")).rstrip("%")) or 0.0,
                       now, evidence_type="getsocials")]
    out.append(observation(company_bq_id, "getsocials.done",
                           float(progress.get("done", 0)), now,
                           evidence_type="getsocials"))
    out.append(observation(company_bq_id, "getsocials.locked",
                           float(progress.get("locked", 0)), now,
                           evidence_type="getsocials"))
    return out
