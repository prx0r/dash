"""Analysis layer — computed insight over templates, teardowns, compliance.

No new manual data: every figure derives from the registries.
- pattern_rollup: per pattern → templates, pains, fixes, stats, compliance load
- readiness: per-template ChatGPT-native coordination score (rule-based, explainable)
- opportunity: ONS vacancy weight × pain density → build priority

Readiness rubric (deterministic, stated plainly):
  start 100 (information layer is fully agent-able)
  -15  physical fulfillment stays human (applies to all: coordination ceiling)
  -5   per compliance_spine requirement (regulatory drag)
  -5   if any marketplace acquisition (platform dependence)
  +5   if any direct/repeat acquisition (owned demand)
  clamp 0..100. This scores COORDINATION readiness, never autonomy:
  fulfillment is physical, judgment regulated, money human-approved.
"""

from __future__ import annotations

from typing import Any

# ONS workforce jobs by SIC section, thousands, via Aug 2026 bulletin
# (JOBS02 through the jobs-and-vacancies release). Static snapshot;
# refresh via kernel.evidence when needed.
ONS_JOBS_SNAPSHOT: dict[str, float] = {
    "Q": 5090.0, "G": 4629.0, "M": 3492.0, "P": 3137.0, "N": 2995.0,
    "I": 2614.0, "C": 2482.0, "F": 2321.0, "H": 1918.0, "O": 1794.0,
    "J": 1577.0, "K": 1112.0, "R": 1104.0, "S": 1041.0, "T": 500.0,
}
ONS_SNAPSHOT_SOURCE = "ONS jobs and vacancies in the UK, Aug 2026 (VACS02/JOBS02 via bulletin)"


def pattern_rollup(templates: Any, teardowns: Any) -> dict[str, Any]:
    """Per-pattern rollup: templates, pains ranked, fixes, stats, compliance load."""
    from agentcom.kernel.teardowns.graph import VERTICAL_PATTERN

    td_by_template = {t.template_id: t for t in teardowns.load_all()}
    rollup: dict[str, Any] = {}
    for tpl in templates.load_all():
        pattern = VERTICAL_PATTERN.get(tpl.vertical, "unclassified")
        node = rollup.setdefault(pattern, {
            "templates": [], "pains": [], "fixes": set(),
            "stats": [], "compliance_count": 0, "margin_leaks": 0,
        })
        node["templates"].append(tpl.template_id)
        td = td_by_template.get(tpl.template_id)
        if not td:
            continue
        for pain in td.raw.get("pain_ranking", []):
            node["pains"].append({"template": tpl.template_id, "rank": pain["rank"],
                                  "pain": pain["pain"], "fix": pain["fix_id"]})
            node["fixes"].add(pain["fix_id"])
        for leak in td.raw.get("margin_leaks", []):
            node["margin_leaks"] += 1
            if leak.get("stat"):
                node["stats"].append({"template": tpl.template_id,
                                      "leak": leak["name"], "stat": leak["stat"],
                                      "basis": leak.get("stat_basis", "")})
        node["compliance_count"] += len(td.raw.get("compliance_spine", []))
    for node in rollup.values():
        node["templates"].sort()
        node["pains"].sort(key=lambda p: (p["rank"], p["template"]))
        node["fixes"] = sorted(node["fixes"])
    return rollup


def readiness_score(teardown: Any) -> dict[str, Any]:
    """Explainable coordination-readiness score for one teardown."""
    deductions: list[str] = []
    score = 100.0
    score -= 15.0
    deductions.append("physical fulfillment stays human (-15)")
    n_comp = len(teardown.raw.get("compliance_spine", []))
    if n_comp:
        score -= 5.0 * n_comp
        deductions.append(f"{n_comp} compliance requirements (-{5 * n_comp})")
    owners = {a.get("owner") for a in teardown.raw.get("acquisition", [])}
    if "marketplace" in owners:
        score -= 5.0
        deductions.append("marketplace-dependent acquisition (-5)")
    if owners & {"direct", "repeat", "referral"}:
        score += 5.0
        deductions.append("owned demand present (+5)")
    return {"template_id": teardown.template_id,
            "score": max(0.0, min(100.0, score)),
            "deductions": deductions}


def readiness_all(teardowns: Any) -> list[dict[str, Any]]:
    ranked = [readiness_score(td) for td in teardowns.load_all()]
    ranked.sort(key=lambda r: (-r["score"], r["template_id"]))
    return ranked


def opportunity_ranking(templates: Any, teardowns: Any,
                        vacancies: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Build priority = ONS vacancy weight of mapped SIC sections × pain density.

    Pain density = 1 + 0.1 × (pains + margin leaks). Deterministic.
    """
    from agentcom.kernel.evidence import template_priority

    vacancies = vacancies or ONS_JOBS_SNAPSHOT
    weights = dict(template_priority(vacancies))
    td_by_template = {t.template_id: t for t in teardowns.load_all()}
    ranked: list[dict[str, Any]] = []
    for tpl in templates.load_all():
        td = td_by_template.get(tpl.template_id)
        pains = len(td.raw.get("pain_ranking", [])) if td else 0
        leaks = len(td.raw.get("margin_leaks", [])) if td else 0
        density = 1.0 + 0.1 * (pains + leaks)
        weight = weights.get(tpl.template_id, 0.0)
        ranked.append({"template_id": tpl.template_id, "vertical": tpl.vertical,
                       "vacancy_weight": weight, "pains": pains,
                       "margin_leaks": leaks,
                       "opportunity": round(weight * density, 1)})
    ranked.sort(key=lambda r: (-r["opportunity"], r["template_id"]))
    return ranked
