"""Metrics pipelines — time-series builders (pure) + push helpers."""
from __future__ import annotations

from typing import Any

from .seed import node, observation, utcnow


def stack_price_observations(tool_id: str, prices: dict[str, float | None],
                             now: str, evidence_type: str = "stack-research",
                             ) -> list[dict]:
    """Quarterly price heartbeat for one TOOL_* node. None = unmeasured."""
    out = []
    for metric, value in prices.items():
        out.append(observation(tool_id, f"price.{metric}", value, now,
                               evidence_type=evidence_type))
    return out


def price_drift_alert(tool_id: str, metric: str, old: float, new: float,
                      now: str) -> dict | None:
    """>10% move → alert observation. Mirrors domain price-drift rule."""
    if not old:
        return None
    ratio = new / old
    if abs(ratio - 1.0) > 0.10:
        return observation(tool_id, f"price.drift_alert:{metric}", ratio, now,
                           evidence_type="stack-research")
    return None


def ons_vacancy_observations(vacancies: dict[str, float], now: str,
                             source: str = "ONS jobs Aug 2026") -> list[dict]:
    """SIC section levels → SIC_* node observations."""
    return [observation(f"SIC_{sic}", "ons.jobs_thousands", value, now,
                        evidence_type="ons-bulletin", source=source)
            for sic, value in vacancies.items()]


def opportunity_observations(ranked: list[dict[str, Any]], now: str,
                             formula_version: str = "opportunity.v2"
                             ) -> list[dict]:
    """Scored ranking → observations on TPL_* nodes. Formula version pinned."""
    from .seed import tpl_node_id
    out = []
    for r in ranked:
        out.append(observation(tpl_node_id(r["template_id"]),
                               f"opportunity.score", r["opportunity"], now,
                               evidence_type=formula_version))
    return out


def sic_nodes(sections: list[str], now: str) -> list[dict]:
    return [node(f"SIC_{s}", "sic_section", {"section": s,
                "verification": "VERIFIED", "basis": "govt-data"}, now)
            for s in sections]
