"""Distill executors — pure functions implementing the 6 protocol ops.

Each executor takes explicit inputs (dicts/lists) and returns outputs.
BQ fetching stays in kernel/bigquery; these never touch the network.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

GATES = [
    "G1_installed_base", "G2_lifecycle_trigger", "G3_compatibility_graph",
    "G4_buyer_selection_autonomy", "G5_local_transactional_supply",
    "G6_decision_ownership_gap", "G7_reseller_path", "G8_economics",
    "G9_validated_demand", "G10_operational_burden",
    "G11_agentic_feed_eligibility", "G12_retrieval_whitespace",
]
REROUTE_TRACKS = {"SERVICE_ORCHESTRATION", "B2B_RESOLUTION", "BENCHMARK"}
TERMINAL = {"PROVEN", "MUTATE", "KILLED"}


def _hid(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


# --- distill-sprawl-scan -------------------------------------------------

def sprawl_scan(inventory: list[dict[str, Any]],
                freshness_windows: dict[str, float] | None = None,
                stale_multiplier: float = 2.0) -> dict[str, Any]:
    """Table inventory → pools + stale/empty flags + coverage gaps."""
    pools: dict[tuple, int] = {}
    flags: list[dict] = []
    for t in inventory:
        rows = t.get("rows", 0) or 0
        if rows == 0:
            flags.append({"table": t.get("table"), "flag": "EMPTY",
                          "reason": "0 rows"})
        pools[(t.get("kind", "unknown"), t.get("country", "ALL"))] = \
            pools.get((t.get("kind", "unknown"), t.get("country", "ALL")), 0) + rows
    return {
        "pools": [{"kind": k, "country": c, "count": n}
                  for (k, c), n in sorted(pools.items())],
        "flags": flags,
        "coverage_gaps": ["Real CPC data", "Real merchant density",
                          "Real supplier costs", "Real CVR data"] if any(
            f["flag"] == "EMPTY" for f in flags) else [],
    }


# --- distill-cluster --------------------------------------------------------

def cluster(candidates: list[dict[str, Any]], min_cluster_size: int = 2,
             signal_keys: tuple = ("mechanism", "problem", "country",
                                   "pattern")) -> dict[str, Any]:
    """Candidates → PROPOSED thesis buckets by shared signals."""
    buckets: dict[tuple, list] = {}
    for c in candidates:
        key = tuple(sorted((k, str(c.get(k, ""))) for k in signal_keys
                           if c.get(k)))
        if key:
            buckets.setdefault(key, []).append(c.get("id"))
    theses = []
    for key, members in sorted(buckets.items()):
        if len(members) >= min_cluster_size:
            sig = dict(key)
            tid = "TH-" + _hid(sorted(members)).upper()[:8]
            theses.append({"thesis_id": tid, "members": sorted(members),
                           "shared_signals": sig, "status": "PROPOSED"})
    return {"theses": theses}


# --- distill-snowball ----------------------------------------------------------

BASIS_RANK = {"verified-2026": 1.0, "govt-data": 0.9, "well-established": 0.7,
              "template-analysis": 0.5}


def snowball(thesis: dict[str, Any],
             evidence_batch: list[dict[str, Any]]) -> dict[str, Any]:
    """Append-only thesis update. History preserved, never rewritten."""
    prior = list(thesis.get("observations", []))
    new_obs = [{"id": f"OBS-{_hid(e).upper()[:8]}", **e}
               for e in evidence_batch]
    all_obs = prior + new_obs
    weights = [BASIS_RANK.get(o.get("basis", "template-analysis"), 0.5)
               for o in all_obs]
    confidence = round(sum(weights) / len(weights), 3) if weights else 0.0
    return {
        "thesis_id": thesis.get("thesis_id"),
        "version": int(thesis.get("version", 0)) + 1,
        "observations": all_obs,
        "confidence": confidence,
        "corrections": list(thesis.get("corrections", [])),
        "supersedes": thesis.get("thesis_id"),
        "prior_version": {"version": thesis.get("version", 0),
                          "confidence": thesis.get("confidence"),
                          "n_observations": len(prior)},
    }


def snowball_correct(thesis_next: dict[str, Any], correction_type: str,
                     note: str) -> dict[str, Any]:
    """Record a correction (downgrade / narrow-scope / add-gate / kill-subclaim)."""
    assert correction_type in ("downgrade", "narrow-scope", "add-gate",
                               "kill-subclaim"), correction_type
    thesis_next = dict(thesis_next)
    thesis_next["corrections"] = list(thesis_next.get("corrections", [])) + [
        {"type": correction_type, "note": note}]
    if correction_type == "downgrade":
        thesis_next["confidence"] = round(thesis_next.get("confidence", 0) * 0.8, 3)
    return thesis_next


# --- distill-gate-check -----------------------------------------------------------

def gate_check(candidate: dict[str, Any]) -> dict[str, Any]:
    """12-gate truth table. Mirrors rubric/campaign_gate.py exactly."""
    track = candidate.get("track")
    if track in REROUTE_TRACKS:
        return {"verdict": "REROUTE", "reason": f"track={track}",
                "failed": [], "unknown": []}
    gates = candidate.get("hard_gates", {})
    missing = [g for g in GATES if g not in gates]
    if missing:
        return {"verdict": "BLOCKED", "reason": "missing gates",
                "failed": [], "unknown": missing}
    invalid = {k: v for k, v in gates.items() if v not in ("PASS", "FAIL", "UNKNOWN")}
    if invalid:
        return {"verdict": "INVALID", "reason": "invalid gate states",
                "failed": [], "unknown": [], "invalid": invalid}
    failed = [g for g in GATES if gates[g] == "FAIL"]
    if failed:
        return {"verdict": "REJECTED", "reason": "fatal gate failed",
                "failed": failed, "unknown": []}
    unknown = [g for g in GATES if gates[g] == "UNKNOWN"]
    if unknown:
        return {"verdict": "BLOCKED", "reason": "unknown gates",
                "failed": [], "unknown": unknown}
    return {"verdict": "ELIGIBLE", "reason": "all gates pass",
            "failed": [], "unknown": []}


# --- distill-campaign-compile --------------------------------------------------------

CAMPAIGN_REQUIRED = ["campaign_id", "schema_version", "track", "country",
                     "atom", "buyer_route", "supplier_strategy",
                     "distribution_strategy", "evidence_requirements",
                     "experiment"]
SECTIONS = ["market", "competitors", "catalog", "pricing", "suppliers", "ads",
            "feed", "landing", "metrics", "next_steps"]


def campaign_compile(eligible: dict[str, Any],
                     template: dict[str, Any] | None = None) -> dict[str, Any]:
    """Eligible thesis → campaign spec. Unknowns explicit TBD:, never invented."""
    thesis = eligible.get("thesis", {})
    evidence = eligible.get("evidence", {})
    campaign_id = thesis.get("thesis_id", "TH-UNKNOWN").replace("TH-", "CAMP-")
    country = thesis.get("country", "TBD:country")
    atom = thesis.get("atom", "TBD:product-atom")
    spec = {
        "campaign_id": campaign_id,
        "schema_version": "v2",
        "track": thesis.get("track", "D2C_COMPATIBILITY_COMMERCE"),
        "country": country,
        "atom": atom,
        "buyer_route": evidence.get("buyer_route", "TBD:buyer-route"),
        "supplier_strategy": evidence.get("supplier_strategy",
                                          "TBD:supplier-strategy"),
        "distribution_strategy": evidence.get("distribution_strategy",
                                              "TBD:distribution"),
        "evidence_bindings": evidence.get("bindings", []),
        "evidence_requirements": evidence.get("requirements", []),
        "experiment": {"budget": "TBD:budget", "success_metric": "orders",
                       "kill_rule": "TBD:kill-rule"},
        "sections": {s: "TBD:" + s for s in SECTIONS},
        "unknowns": sorted(
            [v for v in [country, atom] if str(v).startswith("TBD")]
            + ["TBD:" + s for s in SECTIONS]),
    }
    missing = [k for k in CAMPAIGN_REQUIRED if k not in spec]
    assert not missing, missing
    return spec


# --- distill-refine ---------------------------------------------------------------

def refine(outcome: dict[str, Any]) -> dict[str, Any]:
    """Outcome tier → state transition + reusable priors. Killed preserved."""
    tier = outcome.get("tier")
    metrics = outcome.get("metrics", {})
    campaign_id = outcome.get("campaign_id", "CAMP-UNKNOWN")
    if tier == 3 and metrics.get("resolution_success", 0) >= 0.9:
        to_state, reason = "PROVEN", "tier-3 resolution bar met"
    elif tier == 0 or metrics.get("hard_fail"):
        to_state, reason = "KILLED", metrics.get("kill_reason", "tier-0 proxy failed")
    else:
        to_state, reason = "MUTATE", "mixed tiers — mutate scope/supplier/angle"
    assert to_state in TERMINAL
    priors = {
        "supplier_success_by_class": metrics.get("supplier_success"),
        "buyer_selector_by_component": metrics.get("buyer_selector"),
        "return_rate_by_complexity": metrics.get("return_rate"),
        "gap_patterns": metrics.get("gap_patterns"),
    }
    return {"campaign_id": campaign_id, "to_state": to_state, "reason": reason,
            "tier": tier, "evidence_refs": outcome.get("evidence_refs", []),
            "priors": priors, "preserved": True}
